import React, { useState } from 'react';
import { Upload, FileCode, Download, AlertTriangle, CheckCircle, XCircle, Loader2, FileText, TrendingUp } from 'lucide-react';

const KongGeneratorUI = () => {
  const [file, setFile] = useState(null);
  const [generating, setGenerating] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');

  const handleFileUpload = (e) => {
    const uploadedFile = e.target.files[0];
    if (uploadedFile) {
      setFile(uploadedFile);
      setResult(null);
      setError(null);
    }
  };

  const generateKongConfig = async () => {
    if (!file) {
      setError('Please upload an Apigee proxy ZIP file');
      return;
    }

    setGenerating(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch('http://localhost:5000/api/generate-kong-config', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) throw new Error('Generation failed');

      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError(`Failed to generate Kong config: ${err.message}`);
    } finally {
      setGenerating(false);
    }
  };

  const downloadDeckConfig = async () => {
    try {
      const response = await fetch('http://localhost:5000/api/export-deck-config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ kong_config: result.kong_config })
      });

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'kong-config.yaml';
      a.click();
    } catch (err) {
      setError('Failed to download configuration');
    }
  };

  const downloadReport = async () => {
    try {
      const response = await fetch('http://localhost:5000/api/export-migration-report', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ migration_report: result.migration_report })
      });

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'migration-report.md';
      a.click();
    } catch (err) {
      setError('Failed to download report');
    }
  };

  const getImpactColor = (impact) => {
    const colors = {
      high: 'text-red-600 bg-red-50 border-red-200',
      medium: 'text-yellow-600 bg-yellow-50 border-yellow-200',
      low: 'text-green-600 bg-green-50 border-green-200'
    };
    return colors[impact] || colors.medium;
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-blue-50 to-indigo-100 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="bg-white rounded-xl shadow-2xl overflow-hidden">
          {/* Header */}
          <div className="bg-gradient-to-r from-purple-600 to-indigo-600 p-8 text-white">
            <div className="flex items-center gap-3 mb-2">
              <FileCode className="w-10 h-10" />
              <h1 className="text-3xl font-bold">Kong Configuration Generator</h1>
            </div>
            <p className="text-purple-100">
              Transform Apigee proxies to Kong decK configurations with migration analysis
            </p>
          </div>

          {/* Upload Section */}
          <div className="p-8 border-b">
            <label className="block mb-3 text-sm font-semibold text-gray-700">
              Upload Apigee Proxy Bundle (ZIP)
            </label>
            <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-purple-400 transition-colors">
              <input
                type="file"
                accept=".zip"
                onChange={handleFileUpload}
                className="hidden"
                id="file-upload"
              />
              <label htmlFor="file-upload" className="cursor-pointer">
                <Upload className="w-16 h-16 mx-auto mb-4 text-gray-400" />
                <p className="text-gray-600 font-medium">
                  Click to upload or drag and drop
                </p>
                <p className="text-sm text-gray-500 mt-2">
                  ZIP file containing Apigee proxy bundle
                </p>
              </label>
            </div>
            {file && (
              <div className="mt-4 flex items-center gap-2 text-sm text-gray-600">
                <CheckCircle className="w-4 h-4 text-green-600" />
                <span>Selected: {file.name}</span>
              </div>
            )}

            <button
              onClick={generateKongConfig}
              disabled={generating || !file}
              className="mt-6 w-full bg-gradient-to-r from-purple-600 to-indigo-600 text-white py-4 rounded-lg font-semibold hover:from-purple-700 hover:to-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-3 shadow-lg"
            >
              {generating ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Generating Kong Configuration...
                </>
              ) : (
                <>
                  <FileCode className="w-5 h-5" />
                  Generate Kong Configuration
                </>
              )}
            </button>
          </div>

          {error && (
            <div className="mx-8 mt-6 bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-red-600 mt-0.5" />
              <p className="text-sm text-red-800">{error}</p>
            </div>
          )}

          {result && (
            <div className="p-8">
              {/* Coverage Stats */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
                <div className="bg-gradient-to-br from-green-50 to-green-100 rounded-lg p-4 border border-green-200">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-green-700">Coverage</span>
                    <TrendingUp className="w-5 h-5 text-green-600" />
                  </div>
                  <div className="text-3xl font-bold text-green-800">
                    {result.coverage.coverage_percentage}%
                  </div>
                </div>

                <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg p-4 border border-blue-200">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-blue-700">Auto-Migrated</span>
                    <CheckCircle className="w-5 h-5 text-blue-600" />
                  </div>
                  <div className="text-3xl font-bold text-blue-800">
                    {result.coverage.migrated_policies}
                  </div>
                </div>

                <div className="bg-gradient-to-br from-yellow-50 to-yellow-100 rounded-lg p-4 border border-yellow-200">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-yellow-700">Manual</span>
                    <AlertTriangle className="w-5 h-5 text-yellow-600" />
                  </div>
                  <div className="text-3xl font-bold text-yellow-800">
                    {result.coverage.manual_policies}
                  </div>
                </div>

                <div className="bg-gradient-to-br from-gray-50 to-gray-100 rounded-lg p-4 border border-gray-200">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-gray-700">Not Required</span>
                    <XCircle className="w-5 h-5 text-gray-600" />
                  </div>
                  <div className="text-3xl font-bold text-gray-800">
                    {result.coverage.not_required_policies}
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex gap-4 mb-8">
                <button
                  onClick={downloadDeckConfig}
                  className="flex-1 bg-purple-600 text-white py-3 rounded-lg font-semibold hover:bg-purple-700 transition-colors flex items-center justify-center gap-2 shadow"
                >
                  <Download className="w-5 h-5" />
                  Download Kong Config (YAML)
                </button>
                <button
                  onClick={downloadReport}
                  className="flex-1 bg-indigo-600 text-white py-3 rounded-lg font-semibold hover:bg-indigo-700 transition-colors flex items-center justify-center gap-2 shadow"
                >
                  <FileText className="w-5 h-5" />
                  Download Migration Report
                </button>
              </div>

              {/* Tabs */}
              <div className="border-b mb-6">
                <div className="flex gap-6">
                  {['overview', 'config', 'breaking', 'report'].map((tab) => (
                    <button
                      key={tab}
                      onClick={() => setActiveTab(tab)}
                      className={`pb-3 px-2 font-medium transition-colors ${
                        activeTab === tab
                          ? 'text-purple-600 border-b-2 border-purple-600'
                          : 'text-gray-500 hover:text-gray-700'
                      }`}
                    >
                      {tab === 'overview' && 'Overview'}
                      {tab === 'config' && 'Kong Configuration'}
                      {tab === 'breaking' && 'Breaking Changes'}
                      {tab === 'report' && 'Migration Report'}
                    </button>
                  ))}
                </div>
              </div>

              {/* Tab Content */}
              {activeTab === 'overview' && (
                <div className="space-y-6">
                  <div className="bg-blue-50 rounded-lg p-6 border border-blue-200">
                    <h3 className="text-lg font-semibold mb-4 text-blue-900">
                      Migration Summary
                    </h3>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-gray-600">Total Policies:</span>
                        <span className="ml-2 font-semibold text-gray-900">
                          {result.coverage.total_policies}
                        </span>
                      </div>
                      <div>
                        <span className="text-gray-600">Auto-Migrated:</span>
                        <span className="ml-2 font-semibold text-green-700">
                          {result.coverage.migrated_policies}
                        </span>
                      </div>
                      <div>
                        <span className="text-gray-600">Manual Migration:</span>
                        <span className="ml-2 font-semibold text-yellow-700">
                          {result.coverage.manual_policies}
                        </span>
                      </div>
                      <div>
                        <span className="text-gray-600">Not Required:</span>
                        <span className="ml-2 font-semibold text-gray-700">
                          {result.coverage.not_required_policies}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="bg-gradient-to-r from-purple-50 to-indigo-50 rounded-lg p-6 border border-purple-200">
                    <h3 className="text-lg font-semibold mb-3 text-purple-900">
                      Next Steps
                    </h3>
                    <ol className="space-y-2 text-sm text-gray-700">
                      <li className="flex items-start gap-2">
                        <span className="font-semibold text-purple-600">1.</span>
                        <span>Download the Kong configuration YAML file</span>
                      </li>
                      <li className="flex items-start gap-2">
                        <span className="font-semibold text-purple-600">2.</span>
                        <span>Review breaking changes and manual migration items</span>
                      </li>
                      <li className="flex items-start gap-2">
                        <span className="font-semibold text-purple-600">3.</span>
                        <span>Test the configuration in a Kong development environment</span>
                      </li>
                      <li className="flex items-start gap-2">
                        <span className="font-semibold text-purple-600">4.</span>
                        <span>Deploy using: <code className="bg-white px-2 py-1 rounded text-xs">deck sync -s kong-config.yaml</code></span>
                      </li>
                    </ol>
                  </div>
                </div>
              )}

              {activeTab === 'config' && (
                <div className="bg-gray-900 rounded-lg p-6 overflow-x-auto">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold text-white">
                      Kong decK Configuration
                    </h3>
                    <button
                      onClick={() => navigator.clipboard.writeText(JSON.stringify(result.kong_config, null, 2))}
                      className="text-xs bg-gray-700 text-white px-3 py-1 rounded hover:bg-gray-600"
                    >
                      Copy
                    </button>
                  </div>
                  <pre className="text-green-400 text-xs font-mono overflow-x-auto">
                    {JSON.stringify(result.kong_config, null, 2)}
                  </pre>
                </div>
              )}

              {activeTab === 'breaking' && (
                <div className="space-y-4">
                  {result.breaking_changes.length === 0 ? (
                    <div className="bg-green-50 rounded-lg p-8 text-center border border-green-200">
                      <CheckCircle className="w-12 h-12 mx-auto mb-3 text-green-600" />
                      <p className="text-green-800 font-medium">
                        No breaking changes detected!
                      </p>
                    </div>
                  ) : (
                    result.breaking_changes.map((change, idx) => (
                      <div
                        key={idx}
                        className={`rounded-lg p-5 border ${getImpactColor(change.impact)}`}
                      >
                        <div className="flex items-start justify-between mb-3">
                          <div className="flex items-center gap-2">
                            <AlertTriangle className="w-5 h-5" />
                            <h4 className="font-semibold">{change.category}</h4>
                          </div>
                          <span className="text-xs font-semibold uppercase px-2 py-1 rounded">
                            {change.impact} Impact
                          </span>
                        </div>
                        <p className="text-sm mb-3">{change.description}</p>
                        <div className="bg-white bg-opacity-50 rounded p-3">
                          <p className="text-xs font-medium mb-1">Mitigation:</p>
                          <p className="text-sm">{change.mitigation}</p>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              )}

              {activeTab === 'report' && (
                <div className="bg-white rounded-lg border p-6">
                  <div className="prose max-w-none">
                    <div
                      className="text-sm text-gray-700 whitespace-pre-wrap"
                      dangerouslySetInnerHTML={{
                        __html: result.migration_report.replace(/\n/g, '<br/>')
                      }}
                    />
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Usage Instructions */}
        <div className="mt-8 bg-white rounded-lg shadow-lg p-6">
          <h2 className="text-xl font-bold mb-4 text-gray-800">
            Deployment Instructions
          </h2>
          <div className="space-y-4 text-sm text-gray-700">
            <div>
              <h3 className="font-semibold mb-2">1. Install decK CLI</h3>
              <code className="block bg-gray-900 text-green-400 p-3 rounded">
                curl -sL https://github.com/kong/deck/releases/download/v1.28.2/deck_1.28.2_linux_amd64.tar.gz -o deck.tar.gz<br/>
                tar -xf deck.tar.gz -C /tmp<br/>
                sudo cp /tmp/deck /usr/local/bin/
              </code>
            </div>
            <div>
              <h3 className="font-semibold mb-2">2. Validate Configuration</h3>
              <code className="block bg-gray-900 text-green-400 p-3 rounded">
                deck validate -s kong-config.yaml
              </code>
            </div>
            <div>
              <h3 className="font-semibold mb-2">3. Deploy to Kong</h3>
              <code className="block bg-gray-900 text-green-400 p-3 rounded">
                deck sync -s kong-config.yaml --kong-addr http://localhost:8001
              </code>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default KongGeneratorUI;