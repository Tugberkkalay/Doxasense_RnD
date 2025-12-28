import React from 'react';
import './DocumentList.css';

function DocumentList({ documents, viewMode, onDocumentClick }) {
  const getFileIcon = (modality, mimeType) => {
    if (modality === 'image' || mimeType?.startsWith('image/')) {
      return '🖼️';
    } else if (modality === 'audio' || mimeType?.startsWith('audio/')) {
      return '🎤';
    } else if (modality === 'video' || mimeType?.startsWith('video/')) {
      return '🎥';
    } else if (mimeType?.includes('pdf')) {
      return '📄';
    } else if (mimeType?.includes('word')) {
      return '📃';
    }
    return '📄';
  };

  const formatDate = (dateString) => {
    if (!dateString) return '';
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('tr-TR', {
      day: 'numeric',
      month: 'short',
      year: 'numeric'
    }).format(date);
  };

  const getStatusBadge = (status) => {
    const badges = {
      'processed': '✓ Processed',
      'processing': '⏳ Processing',
      'uploaded': '📎 Uploaded',
      'failed': '✗ Failed'
    };
    return badges[status] || status;
  };

  if (!documents || documents.length === 0) {
    return (
      <div className="empty-state">
        <p>No documents yet. Upload your first document above!</p>
      </div>
    );
  }

  return (
    <div className={`document-list ${viewMode}`}>
      {documents.map((doc) => (
        <div 
          key={doc.id} 
          className="document-card"
          onClick={() => onDocumentClick(doc.id)}
        >
          <div className="card-icon">
            <span className="file-icon">
              {getFileIcon(doc.modality, doc.mime_type)}
            </span>
          </div>
          
          <div className="card-content">
            <h3 className="card-title">{doc.original_name}</h3>
            
            <div className="card-meta">
              <span className="meta-item">{formatDate(doc.created_at)}</span>
              <span className="meta-separator">•</span>
              <span className="meta-item">{doc.modality}</span>
              {doc.size_mb && (
                <>
                  <span className="meta-separator">•</span>
                  <span className="meta-item">{doc.size_mb} MB</span>
                </>
              )}
            </div>

            {doc.tags && doc.tags.length > 0 && (
              <div className="card-tags">
                {doc.tags.slice(0, 3).map((tag, idx) => (
                  <span key={idx} className="tag">{tag}</span>
                ))}
                {doc.tags.length > 3 && (
                  <span className="tag-more">+{doc.tags.length - 3}</span>
                )}
              </div>
            )}

            {doc.summary_preview && (
              <p className="card-summary">{doc.summary_preview}</p>
            )}
          </div>

          <div className="card-status">
            <span className={`status-badge status-${doc.status}`}>
              {getStatusBadge(doc.status)}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}

export default DocumentList;