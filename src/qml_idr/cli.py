#!/usr/bin/env python3
"""
Command-line interface for the QML-IDR pipeline.
"""

import click
import sys
from pathlib import Path
import logging

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from qml_idr.workflows.pipeline import IDRPredictionPipeline
from qml_idr.utils.config import load_config, set_config
from qml_idr.utils.logging import setup_logging

@click.group()
@click.option('--config', '-c', type=click.Path(exists=True), 
              help='Configuration file path')
@click.option('--verbose', '-v', is_flag=True, 
              help='Enable verbose logging')
@click.option('--output-dir', '-o', type=click.Path(), 
              help='Output directory for results')
@click.pass_context
def cli(ctx, config, verbose, output_dir):
    """QML vs CML IDR Prediction Pipeline.
    
    A comprehensive comparison between Quantum Machine Learning (QML) and 
    Classical Machine Learning (CML) for predicting intrinsically disordered 
    regions (IDRs) in the RuBisCO enzyme.
    """
    # Set up context
    ctx.ensure_object(dict)
    
    # Load configuration
    if config:
        config_obj = load_config(config)
        set_config(config_obj)
        ctx.obj['config_path'] = config
    
    # Set up logging
    log_level = 'DEBUG' if verbose else 'INFO'
    logger = setup_logging(level=log_level)
    
    if verbose:
        logger.info("Verbose logging enabled")
    
    # Store common options
    ctx.obj['verbose'] = verbose
    ctx.obj['output_dir'] = output_dir
    ctx.obj['logger'] = logger

@cli.command()
@click.option('--max-fragments', type=int, default=20,
              help='Maximum number of IDR fragments to process')
@click.option('--skip-download', is_flag=True,
              help='Skip PDBbind download (use existing data)')
@click.option('--qml-only', is_flag=True,
              help='Run only quantum ML predictions')
@click.option('--cml-only', is_flag=True,
              help='Run only classical ML predictions')
@click.pass_context
def run(ctx, max_fragments, skip_download, qml_only, cml_only):
    """Run the complete QML vs CML comparison pipeline."""
    
    logger = ctx.obj['logger']
    logger.info("Starting QML vs CML IDR prediction pipeline")
    
    try:
        # Initialize pipeline
        pipeline = IDRPredictionPipeline(
            config_path=ctx.obj.get('config_path'),
            output_dir=ctx.obj.get('output_dir')
        )
        
        # Run pipeline with options
        if qml_only and cml_only:
            raise click.ClickException("Cannot specify both --qml-only and --cml-only")
        
        if qml_only:
            logger.info("Running QML-only pipeline")
            results = pipeline.run_qml_only_pipeline(max_fragments)
        elif cml_only:
            logger.info("Running CML-only pipeline")
            results = pipeline.run_cml_only_pipeline(max_fragments)
        else:
            logger.info("Running full comparison pipeline")
            results = pipeline.run_full_pipeline(max_fragments)
        
        # Print summary
        _print_results_summary(results, logger)
        
        logger.info("Pipeline completed successfully!")
        logger.info(f"Results saved to: {pipeline.output_dir}")
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        if ctx.obj['verbose']:
            import traceback
            traceback.print_exc()
        sys.exit(1)

@cli.command()
@click.argument('results_file', type=click.Path(exists=True))
@click.option('--format', type=click.Choice(['json', 'markdown', 'html']), 
              default='markdown', help='Report format')
@click.pass_context
def analyze(ctx, results_file, format):
    """Analyze existing pipeline results."""
    
    logger = ctx.obj['logger']
    logger.info(f"Analyzing results from: {results_file}")
    
    try:
        # Initialize pipeline
        pipeline = IDRPredictionPipeline(
            config_path=ctx.obj.get('config_path'),
            output_dir=ctx.obj.get('output_dir')
        )
        
        # Load results
        results = pipeline.load_results(results_file)
        
        # Generate analysis
        if 'comparison_results' in results:
            comparison_results = results['comparison_results']
            
            # Generate report in specified format
            if format == 'markdown':
                report_file = pipeline.output_dir / "analysis_report.md"
                pipeline.comparative_analysis.generate_report(comparison_results, report_file)
            elif format == 'json':
                report_file = pipeline.output_dir / "analysis_report.json"
                import json
                with open(report_file, 'w') as f:
                    json.dump(comparison_results, f, indent=2, default=str)
            elif format == 'html':
                report_file = pipeline.output_dir / "analysis_report.html"
                _generate_html_report(comparison_results, report_file)
            
            logger.info(f"Analysis report generated: {report_file}")
        
        else:
            logger.warning("No comparison results found in file")
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        if ctx.obj['verbose']:
            import traceback
            traceback.print_exc()
        sys.exit(1)

@cli.command()
@click.option('--fragments', type=int, default=3,
              help='Number of fragments for test run')
@click.pass_context
def test(ctx, fragments):
    """Run a quick test of the pipeline with minimal data."""
    
    logger = ctx.obj['logger']
    logger.info(f"Running pipeline test with {fragments} fragments")
    
    try:
        # Initialize pipeline with test output directory
        test_output = Path(ctx.obj.get('output_dir', 'results')) / 'test'
        
        pipeline = IDRPredictionPipeline(
            config_path=ctx.obj.get('config_path'),
            output_dir=str(test_output)
        )
        
        # Run pipeline with limited data
        results = pipeline.run_full_pipeline(max_fragments=fragments)
        
        # Print test results
        logger.info("=== TEST RESULTS ===")
        _print_results_summary(results, logger)
        
        logger.info("Test completed successfully!")
        logger.info(f"Test results saved to: {test_output}")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        if ctx.obj['verbose']:
            import traceback
            traceback.print_exc()
        sys.exit(1)

@cli.command()
@click.pass_context
def validate(ctx):
    """Validate the installation and configuration."""
    
    logger = ctx.obj['logger']
    logger.info("Validating QML-IDR installation")
    
    validation_results = []
    
    # Check Python version
    python_version = sys.version_info
    if python_version >= (3, 10):
        validation_results.append(("Python version", "✓", f"{python_version.major}.{python_version.minor}"))
    else:
        validation_results.append(("Python version", "✗", f"{python_version.major}.{python_version.minor} (requires 3.10+)"))
    
    # Check required packages
    required_packages = [
        'qiskit', 'numpy', 'pandas', 'scipy', 'biopython', 
        'h5py', 'matplotlib', 'seaborn', 'click'
    ]
    
    for package in required_packages:
        try:
            __import__(package)
            validation_results.append((f"Package {package}", "✓", "Available"))
        except ImportError:
            validation_results.append((f"Package {package}", "✗", "Missing"))
    
    # Check configuration
    try:
        from qml_idr.utils.config import get_config
        config = get_config()
        validation_results.append(("Configuration", "✓", "Loaded successfully"))
    except Exception as e:
        validation_results.append(("Configuration", "✗", f"Error: {e}"))
    
    # Check output directory permissions
    try:
        output_dir = Path(ctx.obj.get('output_dir', 'results'))
        output_dir.mkdir(parents=True, exist_ok=True)
        test_file = output_dir / '.test_write'
        test_file.touch()
        test_file.unlink()
        validation_results.append(("Output directory", "✓", f"Writable: {output_dir}"))
    except Exception as e:
        validation_results.append(("Output directory", "✗", f"Error: {e}"))
    
    # Print validation results
    logger.info("=== VALIDATION RESULTS ===")
    
    all_passed = True
    for component, status, details in validation_results:
        logger.info(f"{component:.<30} {status} {details}")
        if status == "✗":
            all_passed = False
    
    if all_passed:
        logger.info("All validation checks passed! ✓")
    else:
        logger.warning("Some validation checks failed. Please address the issues above.")
        sys.exit(1)

@cli.command()
@click.pass_context
def clean(ctx):
    """Clean up temporary files and intermediate results."""
    
    logger = ctx.obj['logger']
    logger.info("Cleaning up temporary files")
    
    try:
        import shutil
        
        # Directories to clean
        cleanup_dirs = [
            'data/processed/temp_*',
            'logs/temp_*',
            '.snakemake',
            '__pycache__'
        ]
        
        # Files to clean
        cleanup_files = [
            '.environment_ready',
            '.config_validated',
            'logs/monitor.pid'
        ]
        
        cleaned_count = 0
        
        # Clean directories
        for pattern in cleanup_dirs:
            import glob
            for path in glob.glob(pattern):
                if Path(path).exists():
                    if Path(path).is_dir():
                        shutil.rmtree(path)
                    else:
                        Path(path).unlink()
                    cleaned_count += 1
                    logger.info(f"Removed: {path}")
        
        # Clean files
        for file_path in cleanup_files:
            path = Path(file_path)
            if path.exists():
                path.unlink()
                cleaned_count += 1
                logger.info(f"Removed: {file_path}")
        
        logger.info(f"Cleanup completed. Removed {cleaned_count} items.")
        
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        sys.exit(1)

@cli.command()
@click.pass_context
def info(ctx):
    """Display system and configuration information."""
    
    logger = ctx.obj['logger']
    
    logger.info("=== QML-IDR PIPELINE INFORMATION ===")
    
    # System info
    import platform
    logger.info(f"System: {platform.system()} {platform.release()}")
    logger.info(f"Python: {sys.version}")
    logger.info(f"Architecture: {platform.machine()}")
    
    # Configuration info
    try:
        from qml_idr.utils.config import get_config
        config = get_config()
        logger.info(f"Configuration loaded from: config/config.yaml")
        logger.info(f"Output directory: {config.output.results_dir}")
        logger.info(f"Data directory: {config.output.data_dir}")
        logger.info(f"Max qubits: {config.quantum.simulator.max_qubits}")
        logger.info(f"VQE optimizer: {config.quantum.vqe.optimizer}")
    except Exception as e:
        logger.warning(f"Configuration error: {e}")
    
    # Package versions
    packages_to_check = ['qiskit', 'numpy', 'pandas', 'biopython']
    logger.info("\n=== PACKAGE VERSIONS ===")
    
    for package in packages_to_check:
        try:
            module = __import__(package)
            version = getattr(module, '__version__', 'unknown')
            logger.info(f"{package}: {version}")
        except ImportError:
            logger.info(f"{package}: not installed")

def _print_results_summary(results, logger):
    """Print a summary of pipeline results."""
    
    logger.info("=== PIPELINE RESULTS SUMMARY ===")
    
    # Dataset info
    dataset_info = results.get('dataset_info', {})
    logger.info(f"Dataset: {dataset_info.get('n_fragments', 0)} IDR fragments processed")
    
    # QML results
    qml_results = results.get('qml_results', [])
    qml_successful = len([r for r in qml_results if r.get('converged', False)])
    logger.info(f"QML: {qml_successful}/{len(qml_results)} successful predictions")
    
    # CML results
    cml_results = results.get('cml_results', [])
    cml_successful = len([r for r in cml_results if r.get('converged', False)])
    logger.info(f"CML: {cml_successful}/{len(cml_results)} successful predictions")
    
    # Comparison results
    comparison_results = results.get('comparison_results', {})
    if comparison_results:
        performance_summary = comparison_results.get('performance_summary', {})
        overall_assessment = performance_summary.get('overall_assessment', {})
        
        overall_winner = overall_assessment.get('overall_winner', 'Unknown')
        logger.info(f"Overall winner: {overall_winner}")
        
        # Key recommendations
        recommendations = performance_summary.get('recommendations', [])
        if recommendations:
            logger.info("Key recommendations:")
            for i, rec in enumerate(recommendations[:3], 1):  # Show first 3
                logger.info(f"  {i}. {rec}")

def _generate_html_report(comparison_results, output_file):
    """Generate HTML report from comparison results."""
    
    html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>QML vs CML IDR Prediction Analysis</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
        .header { background: #f0f8ff; padding: 20px; border-radius: 8px; margin-bottom: 30px; }
        .section { margin: 30px 0; }
        .metric { background: #f9f9f9; padding: 15px; margin: 10px 0; border-radius: 5px; }
        .winner { color: #007acc; font-weight: bold; }
        table { border-collapse: collapse; width: 100%; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
        th { background-color: #f2f2f2; }
    </style>
</head>
<body>
    <div class="header">
        <h1>QML vs CML IDR Prediction Analysis</h1>
        <p>Comprehensive comparison between Quantum and Classical Machine Learning approaches</p>
    </div>
"""
    
    # Add performance summary
    performance_summary = comparison_results.get('performance_summary', {})
    overall_assessment = performance_summary.get('overall_assessment', {})
    
    html_content += f"""
    <div class="section">
        <h2>Overall Performance</h2>
        <div class="metric">
            <h3>Winner: <span class="winner">{overall_assessment.get('overall_winner', 'Unknown')}</span></h3>
            <p>QML wins: {overall_assessment.get('qml_wins', 0)} metrics</p>
            <p>CML wins: {overall_assessment.get('cml_wins', 0)} metrics</p>
            <p>Total comparisons: {overall_assessment.get('total_comparisons', 0)}</p>
        </div>
    </div>
"""
    
    # Add recommendations
    recommendations = performance_summary.get('recommendations', [])
    if recommendations:
        html_content += """
    <div class="section">
        <h2>Recommendations</h2>
        <ul>
"""
        for rec in recommendations:
            html_content += f"            <li>{rec}</li>\n"
        
        html_content += """
        </ul>
    </div>
"""
    
    html_content += """
    <footer style="margin-top: 50px; padding-top: 20px; border-top: 1px solid #ccc;">
        <p><em>Generated by QML-IDR Pipeline</em></p>
    </footer>
</body>
</html>
"""
    
    with open(output_file, 'w') as f:
        f.write(html_content)

def main():
    """Main entry point."""
    cli()

if __name__ == '__main__':
    main()