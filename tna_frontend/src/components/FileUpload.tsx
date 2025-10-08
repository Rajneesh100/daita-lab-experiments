import React, { useState } from 'react';
import axios from 'axios';
import './FileUpload.css';

const API_BASE_URL = 'http://localhost:8000';

interface FileUploadProps {
    onFileUploaded: (fileData: any) => void;
}

const FileUpload: React.FC<FileUploadProps> = ({ onFileUploaded }) => {
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [uploading, setUploading] = useState(false);
    const [error, setError] = useState<string>('');

    const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (file) {
            if (file.name.endsWith('.xlsx') || file.name.endsWith('.xls')) {
                setSelectedFile(file);
                setError('');
            } else {
                setError('Please select an Excel file (.xlsx or .xls)');
                setSelectedFile(null);
            }
        }
    };

    const handleUpload = async () => {
        if (!selectedFile) {
            setError('Please select a file first');
            return;
        }

        setUploading(true);
        setError('');

        try {
            const formData = new FormData();
            formData.append('file', selectedFile);

            const response = await axios.post(`${API_BASE_URL}/upload-excel`, formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                },
            });

            onFileUploaded(response.data);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to upload file');
        } finally {
            setUploading(false);
        }
    };

    return (
        <div className="file-upload-container">
            <div className="upload-card">
                <h2>Upload TNA Excel Sheet</h2>
                <p className="upload-description">
                    Select your TNA plan Excel file to begin mapping columns to the dashboard structure.
                </p>

                <div className="file-input-wrapper">
                    <input
                        type="file"
                        id="file-input"
                        accept=".xlsx,.xls"
                        onChange={handleFileSelect}
                        disabled={uploading}
                    />
                    <label htmlFor="file-input" className="file-input-label">
                        {selectedFile ? selectedFile.name : 'Choose Excel File'}
                    </label>
                </div>

                {selectedFile && (
                    <div className="file-info">
                        <p><strong>Selected:</strong> {selectedFile.name}</p>
                        <p><strong>Size:</strong> {(selectedFile.size / 1024).toFixed(2)} KB</p>
                    </div>
                )}

                {error && <div className="error">{error}</div>}

                <button
                    className="upload-button"
                    onClick={handleUpload}
                    disabled={!selectedFile || uploading}
                >
                    {uploading ? 'Uploading...' : 'Upload and Continue'}
                </button>

                <div className="upload-instructions">
                    <h3>Instructions:</h3>
                    <ol>
                        <li>Upload your TNA Excel sheet</li>
                        <li>Specify the row where actual data starts</li>
                        <li>Click on column headers to tag them</li>
                        <li>Map columns to stages and items</li>
                        <li>Extract and create dashboard</li>
                    </ol>
                </div>
            </div>
        </div>
    );
};

export default FileUpload;
