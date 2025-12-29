import React, { useState, useRef } from 'react';
import './UploadArea.css';

function UploadArea({ onUpload }) {
  const [dragActive, setDragActive] = useState(false);
  const [useGPU, setUseGPU] = useState(false);
  const fileInputRef = useRef(null);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      onUpload(e.dataTransfer.files[0]);
    }
  };

  const handleChange = (e) => {
    e.preventDefault();
    if (e.target.files && e.target.files.length > 0) {
      // Handle multiple files
      Array.from(e.target.files).forEach(file => {
        onUpload(file, useGPU);
      });
    }
  };

  const handleClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <div 
      className={`upload-area ${dragActive ? 'drag-active' : ''}`}
      onDragEnter={handleDrag}
      onDragLeave={handleDrag}
      onDragOver={handleDrag}
      onDrop={handleDrop}
      onClick={handleClick}
    >
      <input
        ref={fileInputRef}
        type="file"
        className="file-input"
        onChange={handleChange}
        accept=".pdf,.docx,.doc,.txt,.jpg,.jpeg,.png,.mp3,.wav,.mp4,.mov"
        multiple
      />
      
      <div className="upload-icon">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
          <polyline points="17 8 12 3 7 8"></polyline>
          <line x1="12" y1="3" x2="12" y2="15"></line>
        </svg>
      </div>
      
      <h3>Upload Documents</h3>
      <p className="upload-description">
        Drag & drop files here or click to browse
      </p>
      <p className="upload-formats">
        Supports: PDF, Word, Images, Audio, Video
      </p>
      
      <div className="gpu-toggle-container">
        <label className="gpu-toggle">
          <input
            type="checkbox"
            checked={useGPU}
            onChange={(e) => setUseGPU(e.target.checked)}
          />
          <span className="toggle-slider"></span>
          <span className="toggle-label">
            ⚡ Use GPU Processing {useGPU ? '(Faster, ~$0.001/file)' : '(CPU, Free)'}
          </span>
        </label>
      </div>
    </div>
  );
}

export default UploadArea;