import React from 'react';
import './UploadQueue.css';

function UploadQueue({ items }) {
  const getStatusIcon = (status) => {
    switch(status) {
      case 'uploading': return '⬆️';
      case 'queued': return '⏳';
      case 'processing': return '⚙️';
      case 'completed': return '✓';
      case 'failed': return '✗';
      default: return '•';
    }
  };

  const getStatusColor = (status) => {
    switch(status) {
      case 'uploading': return '#2563EB';
      case 'queued': return '#F59E0B';
      case 'processing': return '#8B5CF6';
      case 'completed': return '#10B981';
      case 'failed': return '#EF4444';
      default: return '#6B7280';
    }
  };

  return (
    <div className="upload-queue">
      <div className="queue-header">
        <h3>Processing Queue</h3>
        <span className="queue-count">{items.length} active</span>
      </div>
      
      <div className="queue-items">
        {items.map((item) => (
          <div key={item.id} className={`queue-item status-${item.status}`}>
            <div className="item-icon" style={{ color: getStatusColor(item.status) }}>
              {getStatusIcon(item.status)}
            </div>
            
            <div className="item-content">
              <div className="item-filename">{item.filename}</div>
              <div className="item-status">
                {item.status === 'uploading' && 'Uploading...'}
                {item.status === 'queued' && 'Queued for processing'}
                {item.status === 'processing' && `Processing... ${item.progress}%`}
                {item.status === 'completed' && 'Completed ✓'}
                {item.status === 'failed' && `Failed: ${item.message}`}
              </div>
            </div>
            
            {(item.status === 'processing' || item.status === 'uploading') && (
              <div className="item-progress">
                <div 
                  className="progress-bar" 
                  style={{ width: `${item.progress}%` }}
                />
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export default UploadQueue;