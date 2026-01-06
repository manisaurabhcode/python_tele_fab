# Add these imports at the top of your server.py (after existing imports)
from services.shared_flow_analyzer import SharedFlowAnalyzer
from services.shared_flow_generator import SharedFlowKongGenerator

# Add these service initializations after your existing service initializations
shared_flow_analyzer = SharedFlowAnalyzer(LLM)
shared_flow_generator = SharedFlowKongGenerator(LLM)

# Update the set_config function to include shared flow services
@app.post('/api/config')
def set_config():
    """Apply runtime LLM overrides and re-init pipeline."""
    global LLM, analyzer, kong_gen, plugin_builder, validator, coverage, step_gen, reporter, qa
    global shared_flow_analyzer, shared_flow_generator  # Add this line
    
    log.info("Set config request received")
    data = request.json or {}
    if 'llm' in data:
        llm_cfg = data['llm']
        os.environ['LLM_PROVIDER'] = llm_cfg.get('provider', os.getenv('LLM_PROVIDER','genaihub_langchain'))
        os.environ['LLM_MODEL']    = llm_cfg.get('model',    os.getenv('LLM_MODEL','anthropic--claude-4-sonnet'))
        os.environ['MAX_TOKENS']   = str(llm_cfg.get('max_tokens', os.getenv('MAX_TOKENS','8000')))
        os.environ['TEMPERATURE']  = str(llm_cfg.get('temperature', os.getenv('TEMPERATURE','0.2')))
    
    # Re-init LLM + services
    LLM = LLMClient.from_env_or_file(SETTINGS)
    analyzer  = ApigeeAnalyzer(LLM)
    kong_gen  = KongConfigGenerator(LLM)
    plugin_builder = PluginBuilder(LLM)
    validator = Validator(LLM)
    coverage  = Coverage(LLM)
    step_gen  = ManualSteps(LLM)
    reporter  = Report(LLM)
    qa        = TestScripts(LLM)
    shared_flow_analyzer = SharedFlowAnalyzer(LLM)  # Add this line
    shared_flow_generator = SharedFlowKongGenerator(LLM)  # Add this line
    
    return jsonify({'status':'ok'})


# ============================================================
# NEW SHARED FLOW ENDPOINTS
# ============================================================

@app.post('/api/analyze-shared-flow')
def api_analyze_shared_flow():
    """
    Analyze Apigee Shared Flow bundle(s).
    Accepts ZIP file(s) containing shared flow definitions.
    Returns detailed analysis of policies, conditions, and flow structure.
    """
    log.info("Shared Flow Analysis request received")
    temp_paths = []
    start = time.time()
    
    try:
        files = request.files.getlist('files')
        if not files:
            return jsonify({'error': 'No shared flow files provided'}), 400
        
        log.debug("Shared flow files posted", extra={"files_count": len(files)})
        
        # Save uploaded files
        for f in files:
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
            f.save(tmp.name)
            temp_paths.append(tmp.name)
        
        # Extract and merge shared flow bundles
        merged_flows = {
            'shared_flow_name': 'combined',
            'xml_files': {},
            'code_files': {},
            'config_files': {},
            'flow_hooks': [],
            'policies': []
        }
        
        for path_idx, zip_path in enumerate(temp_paths):
            log.info(f"Extracting shared flow bundle {path_idx + 1}/{len(temp_paths)}")
            bundle = extractor.extract(zip_path)
            
            # Merge XML files (shared flow definitions)
            merged_flows['xml_files'].update(bundle.get('xml_files', {}))
            merged_flows['code_files'].update(bundle.get('code_files', {}))
            merged_flows['config_files'].update(bundle.get('config_files', {}))
        
        # Analyze shared flow structure
        log.info("Starting shared flow analysis")
        analysis = shared_flow_analyzer.analyze(merged_flows, SETTINGS.get('scoring_rules', {}))
        
        # Add metadata
        analysis['metadata'] = {
            'analyzed_at': datetime.datetime.now().isoformat(),
            'files_processed': len(temp_paths),
            'xml_files_count': len(merged_flows['xml_files']),
            'code_files_count': len(merged_flows['code_files']),
            'analysis_duration_seconds': round(time.time() - start, 2)
        }
        
        log.info("Shared Flow analysis succeeded", extra={
            "xml_files": len(merged_flows['xml_files']),
            "code_files": len(merged_flows['code_files']),
            "policies_found": len(analysis.get('policies', []))
        })
        
        return jsonify({
            'success': True,
            'analysis': analysis,
            'shared_flow_type': 'reusable_flow',
            'can_be_kong_plugin': analysis.get('can_be_kong_plugin', False)
        })
        
    except Exception as e:
        log.exception("Shared Flow analysis failed")
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500
    finally:
        # Cleanup temp files
        for p in temp_paths:
            try:
                os.unlink(p)
            except Exception:
                pass


@app.post('/api/generate-shared-flow-migration')
def api_generate_shared_flow_migration():
    """
    Generate Kong configuration for Apigee Shared Flow.
    This creates reusable Kong plugin bundles or service templates.
    
    Returns:
    - Kong plugin configuration (if shared flow is plugin-worthy)
    - Kong service templates (if shared flow is service-level)
    - Custom Lua plugins for complex logic
    - Integration guide for applying to proxies
    """
    log.info("Shared Flow Migration Generation request received")
    print("🚀 Starting Shared Flow AI-driven migration...")
    tmp_path = None
    
    try:
        up = request.files.get('file')
        if not up:
            return jsonify({'error': 'No shared flow file provided'}), 400
        
        # Save uploaded file
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
        up.save(tmp.name)
        tmp_path = tmp.name
        
        # Phase 1: Extract Shared Flow Bundle
        log.info("Shared Flow Extraction Started", extra={"temp_path": tmp_path})
        bundle = extractor.extract(tmp_path)
        log.info("Shared Flow Extraction Completed", extra={
            "xml_files": len(bundle.get('xml_files', {})),
            "code_files": len(bundle.get('code_files', {}))
        })
        
        # Phase 2: Analyze Shared Flow Structure
        log.info("Shared Flow Analysis Started")
        analysis = shared_flow_analyzer.analyze(bundle, SETTINGS.get('scoring_rules', {}))
        log.info("Shared Flow Analysis Completed")
        
        # Phase 3: Generate Kong Configuration
        log.info("Kong Configuration Generation Started")
        kong_config = shared_flow_generator.generate(analysis)
        kong_config = strip_code_fences(kong_config)
        log.info("Kong Configuration Generation Completed")
        
        # Phase 4: Generate Custom Plugins for Shared Flow Logic
        plugins_out = {}
        start_time = time.time()
        print("🔌 AI generating Kong plugins from shared flow logic... -- Start", "Time:", datetime.datetime.now())
        
        # Check if shared flow should be a plugin
        if analysis.get('recommended_approach') == 'plugin':
            plugin_name = analysis.get('shared_flow_name', 'shared_flow').lower().replace(' ', '_')
            
            # Generate plugin spec from shared flow
            plugin_spec = shared_flow_generator.generate_plugin_spec(analysis)
            plugin_files = plugin_builder.generate_files(plugin_spec)
            
            plugins_out[plugin_name] = "".join([
                f"=== FILE: {k} ===\n{v}\n" 
                for k, v in plugin_files.items()
            ])
            
            log.info(f"Generated Kong plugin: {plugin_name}")
        
        # Process any code files (JS/Python callouts in shared flow)
        for fname, content in (bundle.get('code_files') or {}).items():
            print(f"[generate_shared_flow_plugins] Processing: {fname}")
            
            lang = 'javascript' if fname.endswith('.js') else 'python' if fname.endswith('.py') else 'unknown'
            spec = plugin_builder.distill_spec(fname, lang, analysis, content[:12000])
            files = plugin_builder.generate_files(spec)
            key = (spec.get('plugin_name') or f"sf_custom_{Path(fname).stem}")
            
            plugins_out[key] = "".join([
                f"=== FILE: {k} ===\n{v}\n" 
                for k, v in files.items()
            ])
        
        print("🔌 AI generating Kong plugins... --End", "--- %s seconds ---" % (time.time() - start_time))
        
        # Phase 5: Validation
        log.info("Validation Started")
        val = validator.validate(analysis, kong_config)
        log.info("Validation Completed")
        
        # Phase 6: Coverage Analysis
        log.info("Coverage Analysis Started")
        cov = coverage.compute(analysis, kong_config)
        log.info("Coverage Analysis Completed")
        
        # Generate Statistics
        stats = {
            'total': cov.get('total_policies', 0),
            'auto': len([m for m in cov.get('policy_mappings', []) if m.get('auto_generated')]),
            'bundled': cov.get('bundling_analysis', {}).get('bundled_policies_count', 0),
            'custom': len([m for m in cov.get('policy_mappings', []) if m.get('requires_custom_plugin')]),
            'efficiency': cov.get('bundling_analysis', {}).get('efficiency_gain', 0),
            'coverage_pct': cov.get('coverage_percentage', 0)
        }
        
        # Phase 7: Generate Reports and Integration Guide
        log.info("Report Generation Started")
        rpt = reporter.build(analysis, stats)
        
        # Generate integration guide for shared flows
        integration_guide = shared_flow_generator.generate_integration_guide(
            analysis, 
            kong_config, 
            plugins_out
        )
        
        # Generate test scripts
        tests = qa.build(analysis, kong_config)
        
        print("✨ Shared Flow migration package complete!")
        
        return jsonify({
            'success': True,
            'shared_flow_name': analysis.get('shared_flow_name', 'unknown'),
            'migration_approach': analysis.get('recommended_approach', 'service_template'),
            'kong_config': yaml.safe_load(kong_config),
            'custom_plugins': plugins_out,
            'integration_guide': integration_guide,
            'coverage': cov,
            'validation': val,
            'migration_report': rpt,
            'test_scripts': tests,
            'usage_instructions': {
                'as_plugin': 'Apply this plugin to any Kong service/route',
                'as_template': 'Use this as a template for service configuration',
                'reusability': 'This shared flow can be reused across multiple proxies'
            }
        })
        
    except Exception as e:
        log.exception("Shared Flow migration generation failed")
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


@app.post('/api/export-shared-flow-package')
def api_export_shared_flow_package():
    """
    Export complete shared flow migration package as ZIP.
    Includes:
    - Kong configuration (plugin or service template)
    - Custom Lua plugins
    - Integration guide (how to apply to proxies)
    - Migration report
    - Test scripts
    - README with usage instructions
    """
    log.info("Shared Flow Package Export request received")
    
    try:
        data = request.json or {}
        tmpdir = tempfile.mkdtemp()
        
        # 1. Kong Configuration
        kong_config_path = os.path.join(tmpdir, 'kong-shared-flow-config.yaml')
        with open(kong_config_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(data.get('kong_config', {}), f, default_flow_style=False)
        
        # 2. Custom Plugins
        plugins_root = os.path.join(tmpdir, 'custom-plugins')
        os.makedirs(plugins_root, exist_ok=True)
        
        for name, content in (data.get('custom_plugins') or {}).items():
            pdir = os.path.join(plugins_root, name)
            os.makedirs(pdir, exist_ok=True)
            
            parts = content.split('=== FILE:')
            for part in parts[1:]:
                header, body = part.strip().split('\n', 1)
                filename = header.replace('===', '').strip()
                
                with open(os.path.join(pdir, filename), 'w', encoding='utf-8') as pf:
                    pf.write(body.strip())
        
        # 3. Integration Guide
        integration_path = os.path.join(tmpdir, 'INTEGRATION_GUIDE.md')
        with open(integration_path, 'w', encoding='utf-8') as f:
            f.write(data.get('integration_guide', '# Integration Guide\n\nSee documentation.'))
        
        # 4. Migration Report
        report_path = os.path.join(tmpdir, 'MIGRATION_REPORT.md')
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(data.get('migration_report', ''))
        
        # 5. Test Scripts
        test_path = os.path.join(tmpdir, 'test-shared-flow-migration.sh')
        with open(test_path, 'w', encoding='utf-8') as f:
            f.write(data.get('test_scripts', '#!/bin/bash\necho "Test script"'))
        
        try:
            os.chmod(test_path, 0o755)
        except Exception:
            pass
        
        # 6. Usage Instructions
        usage_path = os.path.join(tmpdir, 'USAGE.md')
        usage_content = f"""# Shared Flow Migration - Usage Instructions

## Shared Flow: {data.get('shared_flow_name', 'Unknown')}
## Migration Approach: {data.get('migration_approach', 'Unknown')}

### Quick Start

1. **Deploy Custom Plugins** (if any)
   ```bash
   # Copy plugins to Kong
   cp -r custom-plugins/* /usr/local/share/lua/5.1/kong/plugins/
   
   # Update kong.conf
   plugins = bundled,{','.join(data.get('custom_plugins', {}).keys())}
   
   # Restart Kong
   kong restart
   ```

2. **Apply Configuration**
   ```bash
   # Using decK
   deck sync -s kong-shared-flow-config.yaml
   ```

3. **Test the Migration**
   ```bash
   ./test-shared-flow-migration.sh
   ```

### Integration with Proxies

{data.get('integration_guide', 'See INTEGRATION_GUIDE.md for details')}

### Coverage Statistics
- Total Policies: {data.get('coverage', {}).get('total_policies', 0)}
- Coverage: {data.get('coverage', {}).get('coverage_percentage', 0)}%
- Custom Plugins: {len(data.get('custom_plugins', {}))}

### Next Steps
1. Review INTEGRATION_GUIDE.md
2. Apply to your Kong services/routes
3. Run tests
4. Monitor Kong logs
"""
        
        with open(usage_path, 'w', encoding='utf-8') as f:
            f.write(usage_content)
        
        # 7. README
        cov = data.get('coverage') or {}
        readme_content = f"""# Kong Shared Flow Migration Package

This package contains the complete migration of Apigee Shared Flow to Kong Gateway.

## Package Contents

- `kong-shared-flow-config.yaml` - Kong declarative configuration
- `custom-plugins/` - Custom Lua plugins (if generated)
- `INTEGRATION_GUIDE.md` - How to apply this to proxies
- `MIGRATION_REPORT.md` - Detailed migration analysis
- `USAGE.md` - Quick start and usage instructions
- `test-shared-flow-migration.sh` - Test scripts

## Shared Flow Information

- **Name**: {data.get('shared_flow_name', 'Unknown')}
- **Migration Approach**: {data.get('migration_approach', 'Unknown')}
- **Total Policies**: {cov.get('total_policies', 0)}
- **Coverage**: {cov.get('coverage_percentage', 0)}%
- **Custom Plugins**: {len(data.get('custom_plugins', {}))}

## Quick Start

```bash
# 1. Deploy plugins (if any)
cp -r custom-plugins/* /usr/local/share/lua/5.1/kong/plugins/

# 2. Apply configuration
deck sync -s kong-shared-flow-config.yaml

# 3. Test
./test-shared-flow-migration.sh
```

## Reusability

This shared flow can be applied to multiple Kong services and routes.
See `INTEGRATION_GUIDE.md` for detailed instructions.

## Support

For issues or questions, refer to the migration report and integration guide.
"""
        
        readme_path = os.path.join(tmpdir, 'README.md')
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        
        # Create ZIP
        zip_path = tmpdir + '.zip'
        shutil.make_archive(tmpdir, 'zip', tmpdir)
        
        log.info("Shared Flow package export completed")
        
        return _flask_send_zip(zip_path)
        
    except Exception as e:
        log.exception("Shared Flow package export failed")
        return jsonify({'error': str(e)}), 500


@app.post('/api/combine-proxy-and-shared-flow')
def api_combine_proxy_and_shared_flow():
    """
    Combine proxy migration with shared flow migration.
    This endpoint accepts both proxy and shared flow bundles,
    analyzes them separately, then combines the Kong configurations.
    
    Use this when you want to migrate a proxy that uses shared flows.
    """
    log.info("Combined Proxy + Shared Flow Migration request received")
    tmp_proxy_path = None
    tmp_sf_paths = []
    
    try:
        # Get proxy file
        proxy_file = request.files.get('proxy')
        shared_flow_files = request.files.getlist('shared_flows')
        
        if not proxy_file:
            return jsonify({'error': 'No proxy file provided'}), 400
        
        # Save proxy
        tmp_proxy = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
        proxy_file.save(tmp_proxy.name)
        tmp_proxy_path = tmp_proxy.name
        
        # Save shared flows
        for sf in shared_flow_files:
            tmp_sf = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
            sf.save(tmp_sf.name)
            tmp_sf_paths.append(tmp_sf.name)
        
        # Extract and analyze proxy
        log.info("Extracting and analyzing proxy")
        proxy_bundle = extractor.extract(tmp_proxy_path)
        proxy_analysis = analyzer.analyze(proxy_bundle, SETTINGS.get('scoring_rules', {}))
        
        # Extract and analyze shared flows
        shared_flow_analyses = []
        for sf_path in tmp_sf_paths:
            log.info(f"Extracting and analyzing shared flow: {sf_path}")
            sf_bundle = extractor.extract(sf_path)
            sf_analysis = shared_flow_analyzer.analyze(sf_bundle, SETTINGS.get('scoring_rules', {}))
            shared_flow_analyses.append(sf_analysis)
        
        # Generate Kong configurations
        log.info("Generating combined Kong configuration")
        proxy_kong = kong_gen.generate(proxy_analysis)
        sf_kong_configs = [
            shared_flow_generator.generate(sf_analysis) 
            for sf_analysis in shared_flow_analyses
        ]
        
        # Combine configurations
        combined_kong_config = shared_flow_generator.combine_configurations(
            proxy_kong,
            sf_kong_configs,
            proxy_analysis,
            shared_flow_analyses
        )
        
        combined_kong_config = strip_code_fences(combined_kong_config)
        
        # Generate all plugins
        all_plugins = {}
        
        # Proxy plugins
        for fname, content in (proxy_bundle.get('code_files') or {}).items():
            lang = 'javascript' if fname.endswith('.js') else 'python' if fname.endswith('.py') else 'unknown'
            spec = plugin_builder.distill_spec(fname, lang, proxy_analysis, content[:12000])
            files = plugin_builder.generate_files(spec)
            key = spec.get('plugin_name') or f"proxy_{Path(fname).stem}"
            all_plugins[key] = "".join([f"=== FILE: {k} ===\n{v}\n" for k, v in files.items()])
        
        # Shared flow plugins
        for idx, sf_analysis in enumerate(shared_flow_analyses):
            if sf_analysis.get('recommended_approach') == 'plugin':
                plugin_name = sf_analysis.get('shared_flow_name', f'sf_{idx}').lower().replace(' ', '_')
                plugin_spec = shared_flow_generator.generate_plugin_spec(sf_analysis)
                plugin_files = plugin_builder.generate_files(plugin_spec)
                all_plugins[plugin_name] = "".join([f"=== FILE: {k} ===\n{v}\n" for k, v in plugin_files.items()])
        
        # Validation and coverage
        val = validator.validate(proxy_analysis, combined_kong_config)
        cov = coverage.compute(proxy_analysis, combined_kong_config)
        
        stats = {
            'total': cov.get('total_policies', 0),
            'auto': len([m for m in cov.get('policy_mappings', []) if m.get('auto_generated')]),
            'bundled': cov.get('bundling_analysis', {}).get('bundled_policies_count', 0),
            'custom': len([m for m in cov.get('policy_mappings', []) if m.get('requires_custom_plugin')]),
            'efficiency': cov.get('bundling_analysis', {}).get('efficiency_gain', 0),
            'coverage_pct': cov.get('coverage_percentage', 0)
        }
        
        # Reports
        rpt = reporter.build(proxy_analysis, stats)
        tests = qa.build(proxy_analysis, combined_kong_config)
        
        log.info("Combined migration completed successfully")
        
        return jsonify({
            'success': True,
            'proxy_name': proxy_analysis.get('proxy_name', 'unknown'),
            'shared_flows_count': len(shared_flow_analyses),
            'kong_config': yaml.safe_load(combined_kong_config),
            'custom_plugins': all_plugins,
            'coverage': cov,
            'validation': val,
            'migration_report': rpt,
            'test_scripts': tests,
            'integration_notes': 'Proxy and shared flows have been combined into a single Kong configuration'
        })
        
    except Exception as e:
        log.exception("Combined migration failed")
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500
    finally:
        # Cleanup
        if tmp_proxy_path:
            try:
                os.unlink(tmp_proxy_path)
            except Exception:
                pass
        for sf_path in tmp_sf_paths:
            try:
                os.unlink(sf_path)
            except Exception:
                pass


# ============================================================
# END OF NEW SHARED FLOW ENDPOINTS
# ============================================================
