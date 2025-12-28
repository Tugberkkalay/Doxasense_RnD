import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';
import UploadArea from './components/UploadArea';
import DocumentList from './components/DocumentList';
import DocumentDetail from './components/DocumentDetail';

const API_BASE = 'http://localhost:8000/api/ingest';

function App() {
  const [documents, setDocuments] = useState([]);
  const [selectedDoc, setSelectedDoc] = useState(null);
  const [loading, setLoading] = useState(false);
  const [viewMode, setViewMode] = useState('grid'); // 'grid' or 'list'
  const [showDetail, setShowDetail] = useState(false);

  // Fetch documents on mount
  useEffect(() => {
    fetchDocuments();
  }, []);

  const fetchDocuments = async () => {
    try {
      const response = await axios.get(`${API_BASE}/documents?limit=50`);
      setDocuments(response.data.documents || []);
    } catch (error) {
      console.error('Error fetching documents:', error);
    }
  };

  const handleUpload = async (file) => {
    setLoading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post(`${API_BASE}/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 300000, // 5 min timeout for large files
      });
      
      alert('✓ Döküman başarıyla yüklendi ve işlendi!');
      fetchDocuments(); // Refresh list
    } catch (error) {
      console.error('Upload error:', error);
      alert('✗ Yükleme başarısız: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  const handleDocumentClick = async (docId) => {
    try {
      const response = await axios.get(`${API_BASE}/document/${docId}`);
      setSelectedDoc(response.data);
      setShowDetail(true);
    } catch (error) {
      console.error('Error fetching document details:', error);
    }
  };

  const closeDetail = () => {
    setShowDetail(false);
    setSelectedDoc(null);
  };

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <div className="header-content">
          <h1 className="logo">DoxaSense MIND</h1>
          <div className="header-actions">
            <button 
              className={`view-toggle ${viewMode === 'grid' ? 'active' : ''}`}
              onClick={() => setViewMode('grid')}
              title="Grid View"
            >
              <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
                <rect x="2" y="2" width="7" height="7" rx="1"/>
                <rect x="11" y="2" width="7" height="7" rx="1"/>
                <rect x="2" y="11" width="7" height="7" rx="1"/>
                <rect x="11" y="11" width="7" height="7" rx="1"/>
              </svg>
            </button>
            <button 
              className={`view-toggle ${viewMode === 'list' ? 'active' : ''}`}
              onClick={() => setViewMode('list')}
              title="List View"
            >
              <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
                <rect x="2" y="3" width="16" height="3" rx="1"/>
                <rect x="2" y="8" width="16" height="3" rx="1"/>
                <rect x="2" y="13" width="16" height="3" rx="1"/>
              </svg>
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="main-content">
        {/* Upload Area */}
        <UploadArea onUpload={handleUpload} loading={loading} />

        {/* Documents Section */}
        <div className="documents-section">
          <div className="section-header">
            <h2>Recent Documents</h2>
            <span className="count">{documents.length} documents</span>
          </div>
          
          <DocumentList 
            documents={documents}
            viewMode={viewMode}
            onDocumentClick={handleDocumentClick}
          />
        </div>
      </main>

      {/* Detail Drawer */}
      {showDetail && selectedDoc && (
        <DocumentDetail doc={selectedDoc} onClose={closeDetail} />
      )}

      {/* Loading Overlay */}
      {loading && (
        <div className="loading-overlay">
          <div className="spinner"></div>
          <p>İşleniyor...</p>
        </div>
      )}
    </div>
  );
}

export default App;