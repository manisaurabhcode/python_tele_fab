import React, { useState } from 'react';
import { Upload, FileText, AlertCircle, CheckCircle, XCircle, Loader2 } from 'lucide-react';

const ApigeeKongAnalyzer = () => {
  const [files, setFiles] = useState([]);
  const [analyzing, setAnalyzing] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const complexityRules = {
    simple: { maxScore: 30, color: 'text-green-600', bg: 'bg-green-50' },
    medium: { maxScore: 70, color: 'text-yellow-600', bg: 'bg-yellow-50' },
    complex: { maxScore: Infinity, color: 'text-red-600', bg: 'bg-red-50' }
  };

  const handleFileUpload = (e) => {
    const uploadedFiles = Array.from(e.target.files);
    setFiles(uploadedFiles);
    setResult(null);
    setError(null);
  };

  const analyzeProxies = async () => {
    if (files.length === 0) {
      setError('Please upload at least one proxy or shared flow zip file');
      return;
    }

    setAnalyzing(true);
    setError(null);

    try {
      const fileContents = await Promise.all(
        files.map(async (file) => {
          const text = await file.text();
          return { name: file.name, content: text };
        })
      );

      const prompt = `You are an expert in API gateway migrations, specifically from Apigee to Kong Gateway.

Analyze the following Apigee proxy/shared flow configurations and determine the migration complexity.

**Scoring Rules (Base Configuration):**
- Each custom policy: +5 points
- JavaScript/Python callout: +10 points
- ServiceCallout policy: +8 points
- Java callout: +15 points
- Complex OAuth/JWT flows: +10 points
- Response/Request transformations (XSLT, JSONToXML): +8 points
- Message logging with custom variables: +5 points
- Quota/SpikeArrest policies: +3 points
- AssignMessage policy: +2 points
- VerifyAPIKey: +2 points
- CORS policy: +1 point
- Cache policies: +4 points
- ExtractVariables with complex regex: +6 points
- Conditional flows (>5 conditions): +7 points
- Shared flows referenced: +3 points each
- Target server endpoints (>3): +5 points
- Custom analytics: +6 points

**Complexity Thresholds:**
- Simple: 0-30 points
- Medium: 31-70 points
- Complex: 71+ points

**Files to Analyze:**
${fileContents.map(f => `File: ${f.name}\nContent Preview: ${f.content.substring(0, 500)}...`).join('\n\n')}

**Required Output Format (JSON only):**
{
  "complexity": "simple|medium|complex",
  "totalScore": <number>,
  "breakdown": [
    {"category": "Policy Name", "count": <number>, "points": <number>}
  ],
  "migrationNotes": [
    "Detailed note about specific challenge or consideration"
  ],
  "notRequiredForMigration": [
    "Policy/feature that Kong doesn't need or handles differently"
  ],
  "kongEquivalents": [
    {"apigeePolicy": "PolicyName", "kongPlugin": "plugin-name", "effort": "low|medium|high"}
  ],
  "estimatedEffort": "X-Y days"
}

Analyze thoroughly and provide accurate scoring.`;

      const response = await fetch('https://api.anthropic.com/v1/messages', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          model: 'claude-sonnet-4-20250514',
          max_tokens: 4000,
          messages: [{ role: 'user', content: prompt }]
        })
      });

      const data = await response.json();
      const analysisText = data.content[0].text;
      
      const jsonMatch = analysisText.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        const analysisResult = JSON.parse(jsonMatch[0]);
        setResult(analysisResult);
      } else {
        throw new Error('Could not parse analysis result');
      }
    } catch (err) {
      setError(`Analysis failed: ${err.message}`);
    } finally {
      setAnalyzing(false);
    }
  };

  const getComplexityConfig = (complexity) => {
    return complexityRules[complexity] || complexityRules.complex;
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-6">
      <div className="max-w-6xl mx-auto">
        <div className="bg-white rounded-lg shadow-xl p-8">
          <div className="flex items-center gap-3 mb-6">
            <FileText className="w-8 h-8 text-indigo-600" />
            <h1 className="text-3xl font-bold text-gray-800">
              Apigee → Kong Migration Analyzer
            </h1>
          </div>

          <div className="mb-8">
            <label className="block mb-2 text-sm font-medium text-gray-700">
              Upload Apigee Proxy/Shared Flow ZIP Files
            </label>
            <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-indigo-400 transition-colors">
              <input
                type="file"
                multiple
                accept=".zip,.xml"
                onChange={handleFileUpload}
                className="hidden"
                id="file-upload"
              />
              <label htmlFor="file-upload" className="cursor-pointer">
                <Upload className="w-12 h-12 mx-auto mb-3 text-gray-400" />
                <p className="text-sm text-gray-600">
                  Click to upload or drag and drop
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  ZIP files containing proxy bundles or XML configurations
                </p>
              </label>
            </div>
            {files.length > 0 && (
              <div className="mt-3">
                <p className="text-sm text-gray-600">
                  {files.length} file(s) selected: {files.map(f => f.name).join(', ')}
                </p>
              </div>
            )}
          </div>

          <button
            onClick={analyzeProxies}
            disabled={analyzing || files.length === 0}
            className="w-full bg-indigo-600 text-white py-3 rounded-lg font-semibold hover:bg-indigo-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
          >
            {analyzing ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Analyzing with Claude...
              </>
            ) : (
              'Analyze Migration Complexity'
            )}
          </button>

          {error && (
            <div className="mt-6 bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-red-600 mt-0.5" />
              <p className="text-sm text-red-800">{error}</p>
            </div>
          )}

          {result && (
            <div className="mt-8 space-y-6">
              <div className={`rounded-lg p-6 ${getComplexityConfig(result.complexity).bg}`}>
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-2xl font-bold text-gray-800">
                    Complexity: <span className={getComplexityConfig(result.complexity).color}>
                      {result.complexity.toUpperCase()}
                    </span>
                  </h2>
                  <div className="text-right">
                    <p className="text-3xl font-bold text-gray-800">{result.totalScore}</p>
                    <p className="text-sm text-gray-600">Total Score</p>
                  </div>
                </div>
                <p className="text-gray-700">
                  <strong>Estimated Effort:</strong> {result.estimatedEffort}
                </p>
              </div>

              <div className="bg-gray-50 rounded-lg p-6">
                <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                  <CheckCircle className="w-5 h-5 text-blue-600" />
                  Score Breakdown
                </h3>
                <div className="space-y-2">
                  {result.breakdown.map((item, idx) => (
                    <div key={idx} className="flex justify-between items-center bg-white p-3 rounded">
                      <span className="text-gray-700">{item.category}</span>
                      <div className="flex items-center gap-4">
                        <span className="text-sm text-gray-500">Count: {item.count}</span>
                        <span className="font-semibold text-indigo-600">{item.points} pts</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="bg-blue-50 rounded-lg p-6">
                <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                  <FileText className="w-5 h-5 text-blue-600" />
                  Migration Notes
                </h3>
                <ul className="space-y-2">
                  {result.migrationNotes.map((note, idx) => (
                    <li key={idx} className="flex items-start gap-2">
                      <span className="text-blue-600 mt-1">•</span>
                      <span className="text-gray-700">{note}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {result.notRequiredForMigration && result.notRequiredForMigration.length > 0 && (
                <div className="bg-green-50 rounded-lg p-6">
                  <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                    <XCircle className="w-5 h-5 text-green-600" />
                    Not Required for Kong Migration
                  </h3>
                  <ul className="space-y-2">
                    {result.notRequiredForMigration.map((item, idx) => (
                      <li key={idx} className="flex items-start gap-2">
                        <span className="text-green-600 mt-1">✓</span>
                        <span className="text-gray-700">{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="bg-purple-50 rounded-lg p-6">
                <h3 className="text-lg font-semibold mb-4">Kong Plugin Equivalents</h3>
                <div className="space-y-2">
                  {result.kongEquivalents.map((equiv, idx) => (
                    <div key={idx} className="bg-white p-3 rounded">
                      <div className="flex justify-between items-center">
                        <div>
                          <p className="font-medium text-gray-800">{equiv.apigeePolicy}</p>
                          <p className="text-sm text-gray-600">→ {equiv.kongPlugin}</p>
                        </div>
                        <span className={`px-3 py-1 rounded text-sm font-medium ${
                          equiv.effort === 'low' ? 'bg-green-100 text-green-800' :
                          equiv.effort === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                          'bg-red-100 text-red-800'
                        }`}>
                          {equiv.effort} effort
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ApigeeKongAnalyzer;