// src/App.tsx
import React, { useState, useEffect } from 'react';
import { AlertCircle, User, FileText, Share2, Trash2, Plus } from 'lucide-react';

const API_BASE = 'http://localhost:8000/api/v1';

// 型定義
interface User {
  email: string;
  name: string;
}

interface Resource {
  id: number;
  uuid: string;
  name: string;
  owner: string;
}

interface ApiError {
  detail: string;
}

// ユーザーリスト（Auth0の代わり）
const USERS: User[] = [
  { email: 'alice@example.com', name: 'Alice' },
  { email: 'bob@example.com', name: 'Bob' },
  { email: 'charlie@example.com', name: 'Charlie' },
];

function App() {
  const [currentUser, setCurrentUser] = useState<User>(USERS[0]);
  const [resources, setResources] = useState<Resource[]>([]);
  const [selectedResource, setSelectedResource] = useState<Resource | null>(null);
  const [newResourceName, setNewResourceName] = useState<string>('');
  const [shareEmail, setShareEmail] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // APIコール用のヘルパー
  const apiCall = async <T,>(url: string, options: RequestInit = {}): Promise<T> => {
    const response = await fetch(`${API_BASE}${url}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        'X-User-Email': currentUser.email,
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error: ApiError = await response.json();
      throw new Error(error.detail || 'API Error');
    }

    return response.json();
  };

  // リソース一覧を取得
  const fetchResources = async (): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiCall<Resource[]>('/resources');
      setResources(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  // リソース詳細を取得
  const fetchResource = async (uuid: string): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiCall<Resource>(`/resources/${uuid}`);
      setSelectedResource(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      setSelectedResource(null);
    } finally {
      setLoading(false);
    }
  };

  // リソースを作成
  const handleCreateResource = async (): Promise<void> => {
    if (!newResourceName.trim()) return;

    setLoading(true);
    setError(null);
    try {
      const data = await apiCall<Resource>('/resources', {
        method: 'POST',
        body: JSON.stringify({ name: newResourceName }),
      });
      setSuccess(`Resource "${data.name}" created successfully!`);
      setNewResourceName('');
      await fetchResources();
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  // リソースを共有
  const handleShareResource = async (): Promise<void> => {
    if (!shareEmail.trim() || !selectedResource) return;

    setLoading(true);
    setError(null);
    try {
      await apiCall(`/resources/${selectedResource.uuid}/share`, {
        method: 'POST',
        body: JSON.stringify({
          user_email: shareEmail,
          relation: 'viewer'
        }),
      });
      setSuccess(`Resource shared with ${shareEmail}!`);
      setShareEmail('');
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  // リソースを削除
  const deleteResource = async (uuid: string): Promise<void> => {
    if (!confirm('Are you sure you want to delete this resource?')) return;

    setLoading(true);
    setError(null);
    try {
      await apiCall(`/resources/${uuid}`, {
        method: 'DELETE',
      });
      setSuccess('Resource deleted successfully!');
      setSelectedResource(null);
      await fetchResources();
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  // Enter キー押下時のハンドラー
  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>, action: () => void): void => {
    if (e.key === 'Enter') {
      action();
    }
  };

  // ユーザー切り替え時にリソース一覧を再取得
  useEffect(() => {
    fetchResources();
    setSelectedResource(null);
  }, [currentUser]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-500 to-purple-600">
      <div className="container mx-auto p-4 max-w-6xl">
        {/* ヘッダー */}
        <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
          <h1 className="text-3xl font-bold text-gray-800 mb-4">
            🔐 OpenFGA Demo with FastAPI
          </h1>

          {/* ユーザー切り替え */}
          <div className="flex items-center gap-4 p-4 bg-gray-50 rounded-lg">
            <span className="font-semibold">Current User:</span>
            <div className="flex gap-2">
              {USERS.map((user) => (
                <button
                  key={user.email}
                  onClick={() => setCurrentUser(user)}
                  className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                    currentUser.email === user.email
                      ? 'bg-indigo-600 text-white'
                      : 'bg-white text-gray-700 hover:bg-gray-100 border'
                  }`}
                >
                  <User className="inline-block w-4 h-4 mr-2" />
                  {user.name}
                </button>
              ))}
            </div>
            <span className="ml-auto text-sm text-gray-600">
              {currentUser.email}
            </span>
          </div>
        </div>

        {/* アラート */}
        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded-lg mb-4 flex items-center">
            <AlertCircle className="w-5 h-5 mr-2" />
            {error}
          </div>
        )}

        {success && (
          <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded-lg mb-4">
            {success}
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* 左側：リソース一覧 */}
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h2 className="text-xl font-bold mb-4">Resources</h2>

            {/* リソース作成 */}
            <div className="mb-6">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={newResourceName}
                  onChange={(e) => setNewResourceName(e.target.value)}
                  onKeyPress={(e) => handleKeyPress(e, handleCreateResource)}
                  placeholder="New resource name"
                  className="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  disabled={loading}
                />
                <button
                  onClick={handleCreateResource}
                  disabled={loading || !newResourceName.trim()}
                  className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Plus className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* リソースリスト */}
            <div className="space-y-2">
              {loading && !resources.length ? (
                <p className="text-gray-500">Loading...</p>
              ) : resources.length === 0 ? (
                <p className="text-gray-500">No resources available. Create one!</p>
              ) : (
                resources.map((resource) => (
                  <div
                    key={resource.uuid}
                    onClick={() => fetchResource(resource.uuid)}
                    className={`p-3 rounded-lg cursor-pointer transition-colors ${
                      selectedResource?.uuid === resource.uuid
                        ? 'bg-indigo-100 border-indigo-300'
                        : 'bg-gray-50 hover:bg-gray-100'
                    } border`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center">
                        <FileText className="w-4 h-4 mr-2 text-gray-600" />
                        <span className="font-medium">{resource.name}</span>
                      </div>
                      {resource.owner === currentUser.email && (
                        <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded">
                          OWNER
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-gray-500 mt-1">
                      Owner: {resource.owner}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* 右側：リソース詳細 */}
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h2 className="text-xl font-bold mb-4">Resource Details</h2>

            {selectedResource ? (
              <div>
                <div className="mb-6 p-4 bg-gray-50 rounded-lg">
                  <h3 className="font-bold text-lg mb-2">{selectedResource.name}</h3>
                  <p className="text-sm text-gray-600">UUID: {selectedResource.uuid}</p>
                  <p className="text-sm text-gray-600">Owner: {selectedResource.owner}</p>
                  <div className="mt-2">
                    {selectedResource.owner === currentUser.email ? (
                      <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded">
                        You are the OWNER
                      </span>
                    ) : (
                      <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
                        You have VIEWER access
                      </span>
                    )}
                  </div>
                </div>

                {/* オーナーのみ表示 */}
                {selectedResource.owner === currentUser.email && (
                  <>
                    {/* 共有機能 */}
                    <div className="mb-6">
                      <h4 className="font-semibold mb-2">Share this resource</h4>
                      <div className="flex gap-2">
                        <input
                          type="email"
                          value={shareEmail}
                          onChange={(e) => setShareEmail(e.target.value)}
                          onKeyPress={(e) => handleKeyPress(e, handleShareResource)}
                          placeholder="user@example.com"
                          className="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                          disabled={loading}
                        />
                        <button
                          onClick={handleShareResource}
                          disabled={loading || !shareEmail.trim()}
                          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
                        >
                          <Share2 className="w-4 h-4 mr-2" />
                          Share
                        </button>
                      </div>
                    </div>

                    {/* 削除ボタン */}
                    <button
                      onClick={() => deleteResource(selectedResource.uuid)}
                      disabled={loading}
                      className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
                    >
                      <Trash2 className="w-4 h-4 mr-2" />
                      Delete Resource
                    </button>
                  </>
                )}

                {/* アクセステスト */}
                <div className="mt-6 p-4 bg-blue-50 rounded-lg">
                  <p className="text-sm font-semibold mb-2">Test access with different users:</p>
                  <div className="flex gap-2">
                    {USERS.map((user) => (
                      <button
                        key={user.email}
                        onClick={() => {
                          setCurrentUser(user);
                          fetchResource(selectedResource.uuid);
                        }}
                        className="text-xs px-3 py-1 bg-white border rounded hover:bg-gray-50"
                      >
                        Try as {user.name}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-gray-500">
                Select a resource from the list to view details
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;