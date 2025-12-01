import React, { useState } from 'react';
import { Upload, FileCode, Download, AlertTriangle, CheckCircle, Loader2, Zap, Package, FileText, Terminal, Layers } from 'lucide-react';

const AIKongGeneratorUI = () => {
  const [file, setFile] = useState(null);
  const [generating, setGenerating] = useState(false);
  const [progress, setProgress] = useState('');
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('coverage');

  const handleFileUpload = (e) => {
    const uploadedFile = e.target.files[0];
    if (uploadedFile) {
      setFile(uploadedFile);
      setResult(null);
      setError(null);
    }
  };

  const generateMigration = async () => {
    if (!file) {
      setError('Please upload an Apigee proxy ZIP file');
      return;
    }

    setGenerating(true);
    setError(null);
    setProgress('Uploading and extracting files...');

    try {
      const formData = new FormData();
      formData.append('file', file);

      setProgress('AI analyzing Apigee configuration...');
      
      const response = await fetch('http://localhost:5000/api/ai-generate-migration', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Generation failed');
      }

      setProgress('AI generating Kong configuration...');
      const data = await response.json();
      
      setProgress('Complete!');
      setResult(data);
    } catch (err) {
      setError(`Failed to generate migration: ${err.message}`);
    } finally {
      setGenerating(false);
      setProgress('');
    }
  };

  const downloadPackage = async () => {
    try {
      const response = await fetch('http://localhost:5000/api/export-complete-package', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(result)
      });

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'kong-migration-package.zip';
      a.click();
    } catch (err) {
      setError('Failed to download package');
    }
  };

  const getPriorityColor = (priority) => {
    const colors = {
      critical: 'bg-red-100 text-red-800 border-red-300',
      high: 'bg-orange-100 text-orange-800 border-orange-300',
      medium: 'bg-yellow-100 text-yellow-800 border-yellow-300',
      low: 'bg-blue-100 text-blue-800 border-blue-300'
    };
    return colors[priority] || colors.medium;
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-purple-50 to-pink-50 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="bg-white rounded-2xl shadow-2xl overflow-hidden">
          {/* Header */}
          <div className="bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 p-8 text-white">
            <div className="flex items-center gap-3 mb-3">
              <Zap className="w-12 h-12" />
              <div>
                <h1 className="text-4xl font-bold">AI-Powered Kong Generator</h1>
                <p className="text-purple-100 mt-1">
                  Intelligent Apigee to Kong migration with policy bundling
                </p>
              </div>
            </div>
            <div className="flex gap-4 mt-4 text-sm">
              <div className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4" />
                <span>Policy Bundling</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4" />
                <span>Custom Plugins</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4" />
                <span>100% AI-Driven</span>
              </div>
            </div>
          </div>

          {/* Upload Section */}
          <div className="p-8 border-b bg-gradient-to-br from-gray-50 to-white">
            <label className="block mb-3 text-sm font-semibold text-gray-700">
              Upload Apigee Proxy Bundle (ZIP)
            </label>
            <div className="border-2 border-dashed border-purple-300 rounded-xl p-8 text-center hover:border-purple-500 transition-all hover:bg-purple-50">
              <input
                type="file"
                accept=".zip"
                onChange={handleFileUpload}
                className="hidden"
                id="file-upload"
              />
              <label htmlFor="file-upload" className="cursor-pointer">
                <Upload className="w-20 h-20 mx-auto mb-4 text-purple-400" />
                <p className="text-gray-700 font-medium text-lg">
                  Drop your Apigee proxy here
                </p>
                <p className="text-sm text-gray-500 mt-2">
                  AI will analyze and generate complete Kong configuration
                </p>
              </label>
            </div>
            {file && (
              <div className="mt-4 flex items-center gap-2 text-sm text-gray-600 bg-green-50 p-3 rounded-lg border border-green-200">
                <CheckCircle className="w-5 h-5 text-green-600" />
                <span className="font-medium">{file.name}</span>
              </div>
            )}

            <button
              onClick={generateMigration}
              disabled={generating || !file}
              className="mt-6 w-full bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 text-white py-4 rounded-xl font-bold text-lg hover:from-indigo-700 hover:via-purple-700 hover:to-pink-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-3 shadow-xl hover:shadow-2xl"
            >
              {generating ? (
                <>
                  <Loader2 className="w-6 h-6 animate-spin" />
                  {progress}
                </>
              ) : (
                <>
                  <Zap className="w-6 h-6" />
                  Generate Migration with AI
                </>
              )}
            </button>
          </div>

          {error && (
            <div className="mx-8 mt-6 bg-red-50 border-2 border-red-200 rounded-xl p-4 flex items-start gap-3">
              <AlertTriangle className="w-6 h-6 text-red-600 mt-0.5 flex-shrink-0" />
              <div>
                <p className="font-semibold text-red-900">Error</p>
                <p className="text-sm text-red-800 mt-1">{error}</p>
              </div>
            </div>
          )}

          {result && (
            <div className="p-8">
              {/* Coverage Stats */}
              <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-8">
                <div className="bg-gradient-to-br from-green-50 to-green-100 rounded-xl p-4 border-2 border-green-200">
                  <div className="text-sm font-medium text-green-700 mb-1">Coverage</div>
                  <div className="text-3xl font-bold text-green-800">
                    {result.coverage.coverage_percentage}%
                  </div>
                  <div className="text-xs text-green-600 mt-1">Migration Success</div>
                </div>

                <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-xl p-4 border-2 border-blue-200">
                  <div className="text-sm font-medium text-blue-700 mb-1">Auto-Migrated</div>
                  <div className="text-3xl font-bold text-blue-800">
                    {result.coverage.auto_migrated}
                  </div>
                  <div className="text-xs text-blue-600 mt-1">Policies</div>
                </div>

                <div className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-xl p-4 border-2 border-purple-200">
                  <div className="text-sm font-medium text-purple-700 mb-1">Bundled</div>
                  <div className="text-3xl font-bold text-purple-800">
                    {result.coverage.bundled_policies}
                  </div>
                  <div className="text-xs text-purple-600 mt-1">
                    {result.coverage.bundling_efficiency}% efficiency
                  </div>
                </div>

                <div className="bg-gradient-to-br from-orange-50 to-orange-100 rounded-xl p-4 border-2 border-orange-200">
                  <div className="text-sm font-medium text-orange-700 mb-1">Custom Plugins</div>
                  <div className="text-3xl font-bold text-orange-800">
                    {result.coverage.requires_custom_plugin}
                  </div>
                  <div className="text-xs text-orange-600 mt-1">AI Generated</div>
                </div>

                <div className="bg-gradient-to-br from-gray-50 to-gray-100 rounded-xl p-4 border-2 border-gray-200">
                  <div className="text-sm font-medium text-gray-700 mb-1">Not Required</div>
                  <div className="text-3xl font-bold text-gray-800">
                    {result.coverage.not_required}
                  </div>
                  <div className="text-xs text-gray-600 mt-1">Policies</div>
                </div>
              </div>

              {/* Download Package Button */}
              <button
                onClick={downloadPackage}
                className="w-full bg-gradient-to-r from-green-600 to-emerald-600 text-white py-4 rounded-xl font-bold text-lg hover:from-green-700 hover:to-emerald-700 transition-all flex items-center justify-center gap-3 shadow-lg hover:shadow-xl mb-8"
              >
                <Package className="w-6 h-6" />
                Download Complete Migration Package (ZIP)
              </button>

              {/* Validation Status */}
              {result.validation && (
                <div className={`mb-8 rounded-xl p-6 border-2 ${
                  result.validation.is_valid
                    ? 'bg-green-50 border-green-200'
                    : 'bg-yellow-50 border-yellow-200'
                }`}>
                  <div className="flex items-center gap-3 mb-3">
                    {result.validation.is_valid ? (
                      <CheckCircle className="w-6 h-6 text-green-600" />
                    ) : (
                      <AlertTriangle className="w-6 h-6 text-yellow-600" />
                    )}
                    <h3 className="font-bold text-lg">
                      {result.validation.is_valid ? 'Configuration Valid' : 'Review Required'}
                    </h3>
                  </div>
                  
                  {result.validation.errors.length > 0 && (
                    <div className="mb-3">
                      <p className="font-semibold text-sm text-red-700 mb-2">Errors to Fix:</p>
                      <ul className="space-y-1">
                        {result.validation.errors.map((err, idx) => (
                          <li key={idx} className="text-sm text-red-600">• {err}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  
                  {result.validation.warnings.length > 0 && (
                    <div>
                      <p className="font-semibold text-sm text-yellow-700 mb-2">Warnings:</p>
                      <ul className="space-y-1">
                        {result.validation.warnings.slice(0, 3).map((warn, idx) => (
                          <li key={idx} className="text-sm text-yellow-600">• {warn}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}

              {/* Tabs */}
              <div className="border-b-2 mb-6">
                <div className="flex gap-2 overflow-x-auto">
                  {[
                    { id: 'coverage', label: 'Policy Mappings', icon: Layers },
                    { id: 'manual', label: 'Manual Steps', icon: Terminal },
                    { id: 'config', label: 'Kong Config', icon: FileCode },
                    { id: 'plugins', label: 'Custom Plugins', icon: Zap },
                    { id: 'report', label: 'Full Report', icon: FileText }
                  ].map(({ id, label, icon: Icon }) => (
                    <button
                      key={id}
                      onClick={() => setActiveTab(id)}
                      className={`pb-3 px-4 font-semibold transition-all flex items-center gap-2 whitespace-nowrap ${
                        activeTab === id
                          ? 'text-purple-600 border-b-4 border-purple-600'
                          : 'text-gray-500 hover:text-gray-700'
                      }`}
                    >
                      <Icon className="w-4 h-4" />
                      {label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Tab Content */}
              {activeTab === 'coverage' && (
                <div className="space-y-4">
                  <div className="bg-blue-50 rounded-xl p-5 border-2 border-blue-200">
                    <h3 className="font-bold text-blue-900 mb-3 flex items-center gap-2">
                      <Layers className="w-5 h-5" />
                      Policy Bundling Analysis
                    </h3>
                    <p className="text-sm text-blue-800">
                      AI bundled <strong>{result.coverage.bundled_policies}</strong> policies, 
                      achieving <strong>{result.coverage.bundling_efficiency}%</strong> efficiency gain.
                      This reduces plugin overhead and improves performance.
                    </p>
                  </div>

                  {result.coverage.policy_details.map((mapping, idx) => (
                    <div key={idx} className="bg-white rounded-xl p-5 border-2 border-gray-200 hover:border-purple-300 transition-all">
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex-1">
                          <div className="flex items-center gap-3 mb-2">
                            <h4 className="font-bold text-gray-900">{mapping.apigee_policy}</h4>
                            <span className="text-xs px-2 py-1 rounded bg-gray-100 text-gray-600">
                              {mapping.apigee_policy_type}
                            </span>
                          </div>
                          <p className="text-sm text-gray-600 mb-2">{mapping.reasoning}</p>
                          
                          {mapping.bundled_with && mapping.bundled_with.length > 0 && (
                            <div className="flex items-center gap-2 mb-2">
                              <Layers className="w-4 h-4 text-purple-600" />
                              <span className="text-xs text-purple-700 font-medium">
                                Bundled with: {mapping.bundled_with.join(', ')}
                              </span>
                            </div>
                          )}
                          
                          <div className="text-sm">
                            <strong className="text-indigo-700">Kong Solution:</strong>{' '}
                            <span className="text-gray-700">{mapping.kong_solution}</span>
                            {mapping.kong_plugin && (
                              <span className="ml-2 px-2 py-0.5 bg-indigo-100 text-indigo-700 rounded text-xs font-mono">
                                {mapping.kong_plugin}
                              </span>
                            )}
                          </div>
                        </div>
                        
                        <div className="flex flex-col items-end gap-2">
                          {mapping.auto_generated ? (
                            <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-xs font-semibold">
                              ✓ Auto
                            </span>
                          ) : (
                            <span className="px-3 py-1 bg-orange-100 text-orange-700 rounded-full text-xs font-semibold">
                              ⚠ Manual
                            </span>
                          )}
                          
                          <div className="text-xs text-gray-500">
                            {Math.round(mapping.confidence * 100)}% confident
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {activeTab === 'manual' && (
                <div className="space-y-4">
                  <div className="bg-yellow-50 rounded-xl p-5 border-2 border-yellow-200 mb-6">
                    <h3 className="font-bold text-yellow-900 mb-2">
                      {result.manual_steps.length} Manual Steps Required
                    </h3>
                    <p className="text-sm text-yellow-800">
                      Follow these steps in order. Critical priority items must be completed first.
                    </p>
                  </div>

                  {result.manual_steps
                    .sort((a, b) => {
                      const priority = { critical: 0, high: 1, medium: 2, low: 3 };
                      return priority[a.priority] - priority[b.priority];
                    })
                    .map((step, idx) => (
                      <div key={idx} className={`rounded-xl p-6 border-2 ${getPriorityColor(step.priority)}`}>
                        <div className="flex items-start justify-between mb-3">
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-full bg-white flex items-center justify-center font-bold">
                              {step.step_number}
                            </div>
                            <div>
                              <h4 className="font-bold text-lg">{step.title}</h4>
                              <div className="flex items-center gap-3 mt-1 text-sm">
                                <span className="font-medium">{step.category}</span>
                                <span>•</span>
                                <span>{step.estimated_time}</span>
                              </div>
                            </div>
                          </div>
                          <span className="px-3 py-1 rounded-full text-xs font-bold uppercase">
                            {step.priority}
                          </span>
                        </div>
                        
                        <p className="text-sm mb-4">{step.description}</p>
                        
                        {step.commands && step.commands.length > 0 && (
                          <div className="bg-gray-900 rounded-lg p-4 mb-3">
                            <p className="text-xs text-gray-400 mb-2 font-semibold">Commands:</p>
                            {step.commands.map((cmd, i) => (
                              <code key={i} className="block text-green-400 text-xs mb-1 font-mono">
                                $ {cmd}
                              </code>
                            ))}
                          </div>
                        )}
                        
                        {step.code_snippets && Object.keys(step.code_snippets).length > 0 && (
                          <div className="mt-3">
                            <p className="text-xs font-semibold mb-2">Code Snippets:</p>
                            {Object.entries(step.code_snippets).map(([filename, code]) => (
                              <div key={filename} className="bg-gray-900 rounded-lg p-3 mb-2">
                                <p className="text-xs text-gray-400 mb-1">{filename}</p>
                                <pre className="text-green-400 text-xs overflow-x-auto">
                                  {code.substring(0, 200)}...
                                </pre>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                </div>
              )}

              {activeTab === 'config' && (
                <div className="bg-gray-900 rounded-xl p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold text-white">Kong decK Configuration</h3>
                    <button
                      onClick={() => navigator.clipboard.writeText(JSON.stringify(result.kong_config, null, 2))}
                      className="text-xs bg-gray-700 text-white px-4 py-2 rounded-lg hover:bg-gray-600"
                    >
                      Copy JSON
                    </button>
                  </div>
                  <pre className="text-green-400 text-xs font-mono overflow-x-auto max-h-96">
                    {JSON.stringify(result.kong_config, null, 2)}
                  </pre>
                </div>
              )}

              {activeTab === 'plugins' && (
                <div className="space-y-4">
                  {Object.keys(result.custom_plugins).length === 0 ? (
                    <div className="bg-green-50 rounded-xl p-8 text-center border-2 border-green-200">
                      <CheckCircle className="w-16 h-16 mx-auto mb-3 text-green-600" />
                      <p className="text-green-800 font-medium text-lg">
                        No custom plugins required!
                      </p>
                      <p className="text-sm text-green-600 mt-2">
                        All policies map to existing Kong plugins
                      </p>
                    </div>
                  ) : (
                    Object.entries(result.custom_plugins).map(([name, content]) => (
                      <div key={name} className="bg-white rounded-xl p-6 border-2 border-purple-200">
                        <div className="flex items-center gap-3 mb-4">
                          <Zap className="w-6 h-6 text-purple-600" />
                          <h4 className="font-bold text-lg text-gray-900">{name}</h4>
                        </div>
                        <div className="bg-gray-900 rounded-lg p-4 max-h-64 overflow-y-auto">
                          <pre className="text-green-400 text-xs font-mono whitespace-pre-wrap">
                            {content.substring(0, 800)}...
                          </pre>
                        </div>
                        <p className="text-xs text-gray-600 mt-3">
                          Complete plugin code included in download package
                        </p>
                      </div>
                    ))
                  )}
                </div>
              )}

              {activeTab === 'report' && (
                <div className="bg-white rounded-xl border-2 border-gray-200 p-6">
                  <div className="prose max-w-none">
                    <div className="text-sm text-gray-700 whitespace-pre-wrap font-mono">
                      {result.migration_report}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Info Footer */}
        <div className="mt-8 bg-white rounded-xl shadow-lg p-6 border-2 border-indigo-100">
          <h2 className="text-xl font-bold mb-4 text-gray-800 flex items-center gap-2">
            <Zap className="w-6 h-6 text-indigo-600" />
            How It Works
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
            <div className="bg-gradient-to-br from-indigo-50 to-purple-50 p-4 rounded-lg border border-indigo-200">
              <div className="font-bold text-indigo-900 mb-2">1. AI Analysis</div>
              <p className="text-gray-700">
                Claude analyzes your Apigee proxy, understanding policies, flows, and custom code
              </p>
            </div>
            <div className="bg-gradient-to-br from-purple-50 to-pink-50 p-4 rounded-lg border border-purple-200">
              <div className="font-bold text-purple-900 mb-2">2. Intelligent Bundling</div>
              <p className="text-gray-700">
                AI bundles multiple policies into optimized Kong plugins for better performance
              </p>
            </div>
            <div className="bg-gradient-to-br from-pink-50 to-red-50 p-4 rounded-lg border border-pink-200">
              <div className="font-bold text-pink-900 mb-2">3. Complete Package</div>
              <p className="text-gray-700">
                Get Kong config, custom plugins, tests, and detailed migration guide
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AIKongGeneratorUI;