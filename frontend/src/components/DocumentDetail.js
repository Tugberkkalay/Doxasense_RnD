import React from 'react';
import './DocumentDetail.css';

function DocumentDetail({ doc, onClose }) {
  const { document: docInfo, normalized_docs } = doc;
  const normalizedDoc = normalized_docs && normalized_docs[0];

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString('tr-TR');
  };

  const formatSize = (bytes) => {
    if (!bytes) return 'N/A';
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
  };

  return (
    <>
      <div className="detail-overlay" onClick={onClose}></div>
      <div className="detail-drawer">
        <div className="detail-header">
          <h2>{docInfo.original_name}</h2>
          <button className="close-btn" onClick={onClose}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>

        <div className="detail-content">
          {/* Basic Info */}
          <section className="detail-section">
            <h3 className="section-title">📋 Metadata</h3>
            <div className="info-grid">
              <div className="info-item">
                <span className="info-label">Type</span>
                <span className="info-value">{normalizedDoc?.modality || 'Unknown'}</span>
              </div>
              <div className="info-item">
                <span className="info-label">Size</span>
                <span className="info-value">{formatSize(docInfo.size_bytes)}</span>
              </div>
              <div className="info-item">
                <span className="info-label">Language</span>
                <span className="info-value">{normalizedDoc?.language || 'N/A'}</span>
              </div>
              <div className="info-item">
                <span className="info-label">Status</span>
                <span className="info-value status">{docInfo.status}</span>
              </div>
              <div className="info-item">
                <span className="info-label">Uploaded</span>
                <span className="info-value">{formatDate(docInfo.created_at)}</span>
              </div>
              <div className="info-item">
                <span className="info-label">Processed</span>
                <span className="info-value">{formatDate(docInfo.processed_at)}</span>
              </div>
            </div>
          </section>

          {/* Tags */}
          {normalizedDoc?.tags && normalizedDoc.tags.length > 0 && (
            <section className="detail-section">
              <h3 className="section-title">🏷️ Tags</h3>
              <div className="tags-container">
                {normalizedDoc.tags.map((tag, idx) => (
                  <span key={idx} className="detail-tag">{tag}</span>
                ))}
              </div>
            </section>
          )}

          {/* Summary */}
          {normalizedDoc?.summary_preview && (
            <section className="detail-section">
              <h3 className="section-title">📝 Summary</h3>
              <p className="summary-text">{normalizedDoc.summary_preview}</p>
            </section>
          )}

          {/* Captions */}
          {normalizedDoc?.captions && normalizedDoc.captions.length > 0 && (
            <section className="detail-section">
              <h3 className="section-title">🖼️ Visual Description</h3>
              <ul className="caption-list">
                {normalizedDoc.captions.map((caption, idx) => (
                  <li key={idx}>{caption}</li>
                ))}
              </ul>
            </section>
          )}

          {/* Extra Metadata */}
          {normalizedDoc?.extra_metadata && Object.keys(normalizedDoc.extra_metadata).length > 0 && (
            <section className="detail-section">
              <h3 className="section-title">🔍 Additional Info</h3>
              <div className="metadata-grid">
                {Object.entries(normalizedDoc.extra_metadata).map(([key, value]) => (
                  <div key={key} className="metadata-item">
                    <span className="metadata-key">{key}:</span>
                    <span className="metadata-value">{JSON.stringify(value)}</span>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Full Text Preview */}
          {normalizedDoc?.main_text_preview && (
            <section className="detail-section">
              <h3 className="section-title">📄 Full Text (Preview)</h3>
              <div className="text-preview">
                {normalizedDoc.main_text_preview}
              </div>
            </section>
          )}

          {/* Processing Info */}
          {normalizedDoc?.processing_time && (
            <section className="detail-section">
              <p className="processing-info">
                Processed in {normalizedDoc.processing_time}s
              </p>
            </section>
          )}
        </div>
      </div>
    </>
  );
}

export default DocumentDetail;