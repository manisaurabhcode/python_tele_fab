
import os
import tempfile
import json
import yaml
from pathlib import Path
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

import logging
import datetime
import time
from services.logging_utils import init_logging, get_logger


# Local services
from services.utils import load_settings
#from services.llm_provider import LLMClient


from services.auth import issue_token, verify_token
from functools import wraps





from uuid import uuid4

import time

app = Flask(__name__)
CORS(app)

SETTINGS = load_settings()


import re

FENCE_RE = re.compile(r"^\s*```(?:yaml|yml)?\s*|\s*```\s*$", re.IGNORECASE | re.MULTILINE)

def strip_code_fences(text: str) -> str:
    """Remove markdown code fences (```yaml ... ```) if present."""
    if not text:
        return text
    # If the whole document is fenced, remove both ends.
    stripped = text.strip()
    # Remove leading triple backticks (optionally with 'yaml')
    stripped = re.sub(r"^\s*```(?:yaml|yml)?\s*\n?", "", stripped, flags=re.IGNORECASE)
    # Remove trailing triple backticks
    stripped = re.sub(r"\n?```\s*$", "", stripped)
    return stripped

def require_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        # Optional: only protect select routes; leave analyzer/generator open if desired
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"error": "Unauthorized"}), 401
        token = auth.replace("Bearer ", "").strip()
        payload = verify_token(token)
        if not payload:
            return jsonify({"error": "Invalid or expired token"}), 401
        # Optionally attach user to request context
        from flask import g
        g.user = payload.get("user")
        return fn(*args, **kwargs)
    return wrapper

@app.post("/api/login")
def api_login():
    data = request.json or {}
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()
    # Simple check via ENV; replace with DB/IdP as needed
    admin_user = os.getenv("ADMIN_USER", "admin")
    admin_pass = os.getenv("ADMIN_PASSWORD", "admin123")
    if username == admin_user and password == admin_pass:
        token = issue_token(username)
        return jsonify({"token": token, "user": {"name": username}})
    return jsonify({"error": "Invalid credentials"}), 401

def _get_correlation_id():
    try:
        hdr = SETTINGS.get("logging", {}).get("correlation_header", "X-Request-ID")
    except Exception:
        hdr = "X-Request-ID"
    # Flask request context might not exist during initialization
    from flask import request
    try:
        cid = request.headers.get(hdr)
        return cid or request.environ.get("HTTP_X_REQUEST_ID") or request.environ.get("request_id") or None
    except Exception:
        return None

# Initialize logging once
init_logging(SETTINGS, get_correlation_id_callable=_get_correlation_id)
from services.llm_provider import LLMClient
from services.apigee_analyzer import BundleExtractor, ApigeeAnalyzer
from services.kong_generator import KongConfigGenerator
from services.plugin_builder import PluginBuilder
from services.validation import Validator
from services.coverage import Coverage
from services.report import Report
from services.test_scripts import TestScripts
from services.manual_steps import ManualSteps


LLM = LLMClient.from_env_or_file(SETTINGS)

log = get_logger("server")

extractor = BundleExtractor()
analyzer  = ApigeeAnalyzer(LLM)
kong_gen  = KongConfigGenerator(LLM)
plugin_builder = PluginBuilder(LLM)
validator = Validator(LLM)
coverage  = Coverage(LLM)
step_gen  = ManualSteps(LLM)
reporter  = Report(LLM)
qa        = TestScripts(LLM)

def _flask_send_zip(zip_path: str):
    """send_file with Flask-version-safe filename argument."""
    try:
        from flask import __version__ as flask_version
        major = int(flask_version.split('.')[0])
    except Exception:
        major = 1  # assume old
    if major >= 2:
        return send_file(zip_path, as_attachment=True,
                         download_name='kong-migration-package.zip',
                         mimetype='application/zip')
    else:
        return send_file(zip_path, as_attachment=True,
                         attachment_filename='kong-migration-package.zip',
                         mimetype='application/zip')


@app.before_request
def assign_request_id():
    """Ensure a correlation id exists for this request (header or generated)."""
    print("before_request")
    hdr = SETTINGS.get("logging", {}).get("correlation_header", "X-Request-ID")
    from flask import g, request
    cid = request.headers.get(hdr)
    if not cid:
        cid = str(uuid4())
    g.correlation_id = cid

# @app.after_request
# def add_correlation_id_header(response):
#     """Return correlation id to clients."""
#     print("after_request")
#     hdr = SETTINGS.get("logging", {}).get("correlation_header", "X-Request-ID")
#     from flask import g
#     try:
#         response.headers[hdr] = getattr(g, "correlation_id", "-")
#     except Exception:
#         response.headers[hdr] = "-"

@app.get('/api/config')
#@require_auth
def get_config():
    # set or propagate correlation id
    return jsonify({'llm': SETTINGS.get('llm'), 'scoring_rules': SETTINGS.get('scoring_rules')})

@app.post('/api/config')
def set_config():
    """Apply runtime LLM overrides and re-init pipeline."""
    global LLM, analyzer, kong_gen, plugin_builder, validator, coverage, step_gen, reporter, qa
    # set or propagate correlation id
    print("set_config")
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
    return jsonify({'status':'ok'})

@app.post('/api/analyze')
def api_analyze():
    """Analyze one or more Apigee proxy ZIPs."""
    log.info("Analyze request received")
    temp_paths = []
    start = time.time()
    # set or propagate correlation id
    

    try:
        files = request.files.getlist('files')
        if not files:
            return jsonify({'error': 'No files provided'}), 400
        for f in files:
            log.debug("Files posted", extra={"files_count": len(files)})
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
            f.save(tmp.name)
            temp_paths.append(tmp.name)
        # Extract & merge
        merged = {'proxy_name':'combined','xml_files':{},'code_files':{},'config_files':{}}
        for p in temp_paths:
            b = extractor.extract(p)
            merged['xml_files'].update(b.get('xml_files',{}))
            merged['code_files'].update(b.get('code_files',{}))
        analysis = analyzer.analyze(merged, SETTINGS.get('scoring_rules',{}))
        
        log.info("Analyze succeeded", extra={"xml_files": len(merged['xml_files']),
                                             "code_files": len(merged['code_files'])})

        return jsonify({'analysis': analysis})
    except Exception as e:
        log.exception("Analyze failed")
        return jsonify({'error': str(e)}), 500
    finally:
        for p in temp_paths:
            try: os.unlink(p)
            except Exception: pass

@app.post('/api/ai-generate-migration')
def api_generate():
    # set or propagate correlation id
    """Full pipeline: analyze → decK YAML → plugins → validation → coverage → report → tests."""
    log.info("AI Generate Migration request received")
    print("🚀 Starting AI-driven migration...")
    tmp_path = None
    try:
        up = request.files.get('file')
        if not up:
            return jsonify({'error':'No file provided'}), 400
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
        up.save(tmp.name)
        tmp_path = tmp.name
        # Phase 1  -- START
        log.info("Extraction Started", extra={"temp_path": tmp_path})
        bundle   = extractor.extract(tmp_path)
        log.info("Extraction Completed", extra={"xml_files": len(bundle.get('xml_files',{})),
                                                "code_files": len(bundle.get('code_files',{}))})
        # Phase 1  -- END
        # Phase 2  -- START
        log.info("Analysis Started")
                                                
        analysis = analyzer.analyze(bundle, SETTINGS.get('scoring_rules',{}))
        log.info("Analysis Completed")
        # Phase 2  -- END
        # Phase 3  -- START
        kong_yaml = kong_gen.generate(analysis)
        
        kong_yaml = strip_code_fences(kong_yaml)

        # Plugins from callouts
        # Phase 3  -- END
        # Phase 4  -- START
        plugins_out = {}
        start_time = time.time()
        print("🔌 AI generating custom Lua plugins... -- Start", "Time :", datetime.datetime.now())
        
        for fname, content in (bundle.get('code_files') or {}).items():
            print(f"[generate_custom_plugins] Processing: {fname}")

            lang = 'javascript' if fname.endswith('.js') else 'python' if fname.endswith('.py') else 'unknown'
            spec  = plugin_builder.distill_spec(fname, lang, analysis, content[:12000])
            files = plugin_builder.generate_files(spec)
            key   = (spec.get('plugin_name') or f"custom_{Path(fname).stem}")
            plugins_out[key] = "".join([f"=== FILE: {k} ===\n{v}\n" for k,v in files.items()])
        # Phase 4  -- END
        # Phase 5  -- START
        # Validation & coverage
        print("🔌 AI generating custom Lua plugins... --End", "--- %s seconds ---" % (time.time() - start_time))
        
        
        val = validator.validate(analysis, kong_yaml)
        # Phase 5  -- END
        #Manual Script
        # Phase 6  -- START
        cov = coverage.compute(analysis, kong_yaml)

        #To upddate in future
        #manual_steps = step_gen.m_steps(analysis, cov, plugins_out)
        # Report & tests
        stats = {
            'total': cov.get('total_policies',0),
            'auto':  len([m for m in cov.get('policy_mappings',[]) if m.get('auto_generated')]),
            'bundled': cov.get('bundling_analysis',{}).get('bundled_policies_count',0),
            'custom':  len([m for m in cov.get('policy_mappings',[]) if m.get('requires_custom_plugin')]),
            'efficiency': cov.get('bundling_analysis',{}).get('efficiency_gain',0),
            'coverage_pct': cov.get('coverage_percentage',0)
        }
        # Phase 6  -- END
        # Final report & tests 
        rpt   = reporter.build(analysis, stats)
        tests = qa.build(analysis, kong_yaml)
        print("✨ Migration package complete!")
        
        return jsonify({
            'kong_config': yaml.safe_load(kong_yaml),
            'custom_plugins': plugins_out,
            'coverage': cov,
            'manual_steps': [],
            'validation': val,
            'migration_report': rpt,
            'test_scripts': tests
        })
    except Exception as e:
        import traceback
        return jsonify({'error':str(e),'traceback': traceback.format_exc()}), 500
    finally:
        if tmp_path:
            try: os.unlink(tmp_path)
            except Exception: pass

@app.post('/api/export-complete-package')
def api_export():
    """Export full package as ZIP (decK YAML + plugins + report + steps + tests)."""
    # set or propagate correlation id
    try:
        data = request.json or {}
        import tempfile, shutil
        tmpdir = tempfile.mkdtemp()
        # Kong config
        with open(os.path.join(tmpdir,'kong-config.yaml'),'w',encoding='utf-8') as f:
            yaml.safe_dump(data.get('kong_config',{}), f, default_flow_style=False)
        # Plugins
        plugins_root = os.path.join(tmpdir,'custom-plugins')
        os.makedirs(plugins_root, exist_ok=True)
        for name, content in (data.get('custom_plugins') or {}).items():
            pdir = os.path.join(plugins_root, name)
            os.makedirs(pdir, exist_ok=True)
            parts = content.split('=== FILE:')
            for part in parts[1:]:
                header, body = part.strip().split('\n',1)
                filename = header.replace('===','').strip()
                with open(os.path.join(pdir, filename),'w',encoding='utf-8') as pf:
                    pf.write(body.strip())
        # Report
        with open(os.path.join(tmpdir,'MIGRATION_REPORT.md'),'w',encoding='utf-8') as f:
            f.write(data.get('migration_report',''))
        # Steps
        with open(os.path.join(tmpdir,'MANUAL_STEPS.json'),'w',encoding='utf-8') as f:
            json.dump(data.get('manual_steps',[]), f, indent=2)
        # Tests
        tpath = os.path.join(tmpdir,'test-migration.sh')
        with open(tpath,'w',encoding='utf-8') as f:
            f.write(data.get('test_scripts',''))
        try: os.chmod(tpath, 0o755)
        except Exception: pass
        # README
        cov = data.get('coverage') or {}
        readme = f"""# Kong Migration Package

- kong-config.yaml
- custom-plugins/
- MIGRATION_REPORT.md
- MANUAL_STEPS.json
- test-migration.sh

## Coverage
- Total Policies: {cov.get('total_policies',0)}
- Coverage: {cov.get('coverage_percentage',0)}%
- Bundling Efficiency: {cov.get('bundling_analysis',{}).get('efficiency_gain',0)}
"""
        with open(os.path.join(tmpdir,'README.md'),'w',encoding='utf-8') as f:
            f.write(readme)
        # ZIP
        zip_path = tmpdir + '.zip'
        shutil.make_archive(tmpdir, 'zip', tmpdir)
        return _flask_send_zip(zip_path)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print('Starting Apigee→Kong server (multi-LLM) on http://localhost:5000')
    app.run(port=5000, debug=True)
