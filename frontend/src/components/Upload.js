import React, { useState } from 'react';
import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

const Upload = () => {
    const [file, setFile] = useState(null);
    const [uploading, setUploading] = useState(false);
    const [result, setResult] = useState(null);
    const [error, setError] = useState(null);

    const handleFileChange = (e) => {
        const selectedFile = e.target.files[0];
        if (selectedFile && selectedFile.type === 'application/pdf') {
            setFile(selectedFile);
            setError(null);
            setResult(null);
        } else {
            setError('Please select a valid PDF file');
            setFile(null);
        }
    };

    const handleUpload = async () => {
        if (!file) {
            setError('Please select a PDF file');
            return;
        }

        setUploading(true);
        setError(null);
        setResult(null);

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await axios.post(`${API_BASE}/upload-pdf`, formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                },
            });

            setResult(response.data);
            setFile(null);
            // Reset file input
            document.getElementById('file-input').value = '';
        } catch (error) {
            setError(error.response?.data?.detail || 'Failed to upload PDF');
            console.error('Upload error:', error);
        } finally {
            setUploading(false);
        }
    };

    const handleDrop = (e) => {
        e.preventDefault();
        const droppedFile = e.dataTransfer.files[0];
        if (droppedFile && droppedFile.type === 'application/pdf') {
            setFile(droppedFile);
            setError(null);
            setResult(null);
        } else {
            setError('Please drop a valid PDF file');
        }
    };

    const handleDragOver = (e) => {
        e.preventDefault();
    };

    return (
        <div className="upload">
            <div className="upload-container">
                <h1>Upload Purchase Order PDF</h1>

                <div
                    className={`upload-area ${file ? 'has-file' : ''}`}
                    onDrop={handleDrop}
                    onDragOver={handleDragOver}
                >
                    <div className="upload-content">
                        <div className="upload-icon">📄</div>
                        <p>Drag and drop your PDF here, or click to browse</p>
                        <input
                            id="file-input"
                            type="file"
                            accept=".pdf"
                            onChange={handleFileChange}
                            className="file-input"
                        />
                        <label htmlFor="file-input" className="file-input-label">
                            Choose PDF File
                        </label>
                    </div>

                    {file && (
                        <div className="selected-file">
                            <p>Selected: {file.name}</p>
                            <p>Size: {(file.size / 1024 / 1024).toFixed(2)} MB</p>
                        </div>
                    )}
                </div>

                <div className="upload-actions">
                    <button
                        onClick={handleUpload}
                        disabled={!file || uploading}
                        className="upload-btn"
                    >
                        {uploading ? 'Processing...' : 'Upload and Process'}
                    </button>
                </div>

                {error && (
                    <div className="upload-error">
                        <h3>Error</h3>
                        <p>{error}</p>
                    </div>
                )}

                {result && (
                    <div className="upload-result">
                        <h3>Upload Successful!</h3>
                        <div className="result-details">
                            <p><strong>Message:</strong> {result.message}</p>
                            <p><strong>Order ID:</strong> {result.order_id}</p>
                            {result.is_duplicate && (
                                <p className="duplicate-notice">
                                    ⚠️ This was a duplicate order and existing data was updated.
                                </p>
                            )}

                            {result.parsed_data && (
                                <div className="parsed-preview">
                                    <h4>Parsed Data Preview:</h4>
                                    <div className="preview-grid">
                                        <div className="preview-item">
                                            <label>PO ID:</label>
                                            <span>{result.parsed_data.purchase_order_id}</span>
                                        </div>
                                        <div className="preview-item">
                                            <label>Order Date:</label>
                                            <span>{result.parsed_data.order_date}</span>
                                        </div>
                                        <div className="preview-item">
                                            <label>Buyer:</label>
                                            <span>{result.parsed_data.buyer?.name}</span>
                                        </div>
                                        <div className="preview-item">
                                            <label>Total Amount:</label>
                                            <span>${result.parsed_data.total_amount}</span>
                                        </div>
                                        <div className="preview-item">
                                            <label>Line Items:</label>
                                            <span>{result.parsed_data.line_items?.length || 0} items</span>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default Upload;
