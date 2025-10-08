import React, { useState } from 'react';
import './App.css';
import FileUpload from './components/FileUpload';
import ExcelViewer from './components/ExcelViewer';

interface UploadedFile {
  file_id: string;
  filename: string;
  rows: number;
  columns: number;
  data: any[][];
}

function App() {
  const [uploadedFile, setUploadedFile] = useState<UploadedFile | null>(null);

  const handleFileUploaded = (fileData: UploadedFile) => {
    setUploadedFile(fileData);
  };

  const handleBack = () => {
    setUploadedFile(null);
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>TNA Plan Mapper</h1>
        <p>Upload and map your TNA Excel sheets to dashboard structure</p>
      </header>

      <main className="App-main">
        {!uploadedFile ? (
          <FileUpload onFileUploaded={handleFileUploaded} />
        ) : (
          <ExcelViewer fileData={uploadedFile} onBack={handleBack} />
        )}
      </main>
    </div>
  );
}

export default App;