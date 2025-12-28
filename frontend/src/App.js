import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';
import UploadArea from './components/UploadArea';
import DocumentList from './components/DocumentList';
import DocumentDetail from './components/DocumentDetail';
import UploadQueue from './components/UploadQueue';

// Use relative path for API calls (works in both dev and production)
const API_BASE = '/api/ingest';

function App() {
  const [documents, setDocuments] = useState([]);
  const [selectedDoc, setSelectedDoc] = useState(null);
  const [uploadQueue, setUploadQueue] = useState([]); // Active uploads with status
  const [viewMode, setViewMode] = useState('grid'); // 'grid' or 'list'
  const [showDetail, setShowDetail] = useState(false);

  // Fetch documents on mount
  useEffect(() => {
    fetchDocuments();
  }, []);

  // Poll upload statuses
  useEffect(() => {
    if (uploadQueue.length === 0) return;
    
    const interval = setInterval(() => {
      checkUploadStatuses();
    }, 2000); // Check every 2 seconds
    
    return () => clearInterval(interval);
  }, [uploadQueue]);

  const fetchDocuments = async () => {
    try {
      const response = await axios.get(`${API_BASE}/documents?limit=50`);
      setDocuments(response.data.documents || []);
    } catch (error) {
      console.error('Error fetching documents:', error);
    }
  };

  const checkUploadStatuses = async () => {
    const updatedQueue = await Promise.all(
      uploadQueue.map(async (item) => {
        if (item.status === 'completed' || item.status === 'failed') {
          return item; // Already finished
        }
        
        try {
          const response = await axios.get(`${API_BASE}/job/${item.jobId}/status`);
          const jobStatus = response.data;
          
          return {
            ...item,
            status: jobStatus.status,
            progress: jobStatus.progress || 0,
            message: jobStatus.result?.message || '',
          };
        } catch (error) {
          return item;
        }
      })
    );
    
    setUploadQueue(updatedQueue);
    
    // Refresh document list if any completed
    const hasCompleted = updatedQueue.some((item, idx) => 
      item.status === 'completed' && uploadQueue[idx]?.status !== 'completed'
    );
    
    if (hasCompleted) {
      fetchDocuments();
    }
    
    // Remove completed items after 5 seconds
    setTimeout(() => {
      setUploadQueue(prev => 
        prev.filter(item => 
          !(item.status === 'completed' && Date.now() - item.completedAt > 5000)
        )
      );
    }, 5000);
  };

  const handleUpload = async (file) => {
    const uploadId = Date.now().toString();
    
    // Add to queue immediately
    setUploadQueue(prev => [...prev, {
      id: uploadId,
      filename: file.name,
      status: 'uploading',
      progress: 0,
      jobId: null,
      documentId: null,
    }]);
    
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post(`${API_BASE}/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 30000, // 30 sec for upload
      });
      
      // Update with job info
      setUploadQueue(prev => prev.map(item =>
        item.id === uploadId ? {
          ...item,
          status: 'queued',
          jobId: response.data.job_id,
          documentId: response.data.document_id,
        } : item
      ));
      
    } catch (error) {
      console.error('Upload error:', error);
      setUploadQueue(prev => prev.map(item =>
        item.id === uploadId ? {
          ...item,
          status: 'failed',
          message: error.response?.data?.detail || error.message,
        } : item
      ));
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
        <UploadArea onUpload={handleUpload} />
        
        {/* Upload Queue */}
        {uploadQueue.length > 0 && (
          <UploadQueue items={uploadQueue} />
        )}

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
    </div>
  );
}

export default App;