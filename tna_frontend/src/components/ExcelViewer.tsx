import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './ExcelViewer.css';
import TaggingModal from './TaggingModal';

const API_BASE_URL = 'http://localhost:8000';

interface ExcelViewerProps {
    fileData: {
        file_id: string;
        filename: string;
        rows: number;
        columns: number;
        data: any[][];
    };
    onBack: () => void;
}

interface CellTag {
    column_index: number;
    column_name: string;
    tag_type: string;
    stage_name?: string;
    stage_config?: any;
    item_config?: any;
}

interface ColumnMapping {
    file_id: string;
    filename: string;
    data_start_row: number;
    tags: CellTag[];
}

const ExcelViewer: React.FC<ExcelViewerProps> = ({ fileData, onBack }) => {
    const [dataStartRow, setDataStartRow] = useState<number>(2);
    const [tags, setTags] = useState<CellTag[]>([]);
    const [selectedCell, setSelectedCell] = useState<{ row: number, col: number } | null>(null);
    const [showTagModal, setShowTagModal] = useState(false);
    const [saving, setSaving] = useState(false);
    const [extracting, setExtracting] = useState(false);
    const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);
    const [usedStages, setUsedStages] = useState<string[]>([]);

    useEffect(() => {
        // Load existing mapping if available
        loadMapping();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [fileData.file_id]);

    const loadMapping = async () => {
        try {
            const response = await axios.get(`${API_BASE_URL}/get-mapping/${fileData.file_id}`);
            if (response.data.tags && response.data.tags.length > 0) {
                setTags(response.data.tags);
                setDataStartRow(response.data.data_start_row || 2);

                // Extract unique stage names
                const stages = response.data.tags
                    .filter((tag: CellTag) => tag.stage_name)
                    .map((tag: CellTag) => tag.stage_name)
                    .filter((name: string | undefined, index: number, self: (string | undefined)[]) =>
                        name && self.indexOf(name) === index
                    ) as string[];
                setUsedStages(stages);
            }
        } catch (error) {
            console.error('Error loading mapping:', error);
        }
    };

    const handleCellClick = (rowIndex: number, colIndex: number) => {
        // Only allow tagging header rows (before data start row)
        if (rowIndex >= dataStartRow) {
            setMessage({ type: 'error', text: 'You can only tag header rows. Please adjust the data start row if needed.' });
            return;
        }

        setSelectedCell({ row: rowIndex, col: colIndex });
        setShowTagModal(true);
    };

    const handleTagSave = (tagData: CellTag) => {
        // Remove existing tag for this column if any
        const newTags = tags.filter(t => t.column_index !== tagData.column_index);
        newTags.push(tagData);
        setTags(newTags);

        // Update used stages
        if (tagData.stage_name && !usedStages.includes(tagData.stage_name)) {
            setUsedStages([...usedStages, tagData.stage_name]);
        }

        setShowTagModal(false);
        setSelectedCell(null);
        setMessage({ type: 'success', text: 'Tag saved successfully' });
        setTimeout(() => setMessage(null), 3000);
    };

    const handleRemoveTag = (columnIndex: number) => {
        setTags(tags.filter(t => t.column_index !== columnIndex));
        setMessage({ type: 'success', text: 'Tag removed' });
        setTimeout(() => setMessage(null), 3000);
    };

    const handleSaveMapping = async () => {
        setSaving(true);
        setMessage(null);

        try {
            const mapping: ColumnMapping = {
                file_id: fileData.file_id,
                filename: fileData.filename,
                data_start_row: dataStartRow,
                tags: tags
            };

            await axios.post(`${API_BASE_URL}/save-mapping`, mapping);
            setMessage({ type: 'success', text: 'Mapping saved successfully!' });
        } catch (error: any) {
            setMessage({ type: 'error', text: error.response?.data?.detail || 'Failed to save mapping' });
        } finally {
            setSaving(false);
        }
    };

    const handleExtractAndCreate = async () => {
        // Validate required tags
        const hasIO = tags.some(t => t.tag_type === 'io');
        const hasStyle = tags.some(t => t.tag_type === 'style');
        const hasColor = tags.some(t => t.tag_type === 'color');

        if (!hasIO || !hasStyle || !hasColor) {
            setMessage({ type: 'error', text: 'Please tag io, style, and color columns before extracting' });
            return;
        }

        const hasStages = tags.some(t => t.stage_name);
        if (!hasStages) {
            setMessage({ type: 'error', text: 'Please tag at least one stage before extracting' });
            return;
        }

        setExtracting(true);
        setMessage(null);

        try {
            // First save the mapping
            await handleSaveMapping();

            // Then extract and create dashboard
            const response = await axios.post(`${API_BASE_URL}/extract-and-create-dashboard/${fileData.file_id}`);

            setMessage({
                type: 'success',
                text: `Dashboard created successfully! ${response.data.tna_count} TNA items extracted.`
            });
        } catch (error: any) {
            setMessage({ type: 'error', text: error.response?.data?.detail || 'Failed to extract data' });
        } finally {
            setExtracting(false);
        }
    };

    const getColumnTag = (colIndex: number): CellTag | undefined => {
        return tags.find(t => t.column_index === colIndex);
    };

    const getCellClassName = (rowIndex: number, colIndex: number): string => {
        const classes = ['excel-cell'];

        if (rowIndex < dataStartRow) {
            classes.push('header-cell');
        }

        if (rowIndex === dataStartRow) {
            classes.push('data-start-row');
        }

        const tag = getColumnTag(colIndex);
        if (tag) {
            classes.push('tagged-cell');
            classes.push(`tag-${tag.tag_type}`);
        }

        return classes.join(' ');
    };

    const renderTagBadge = (tag: CellTag) => {
        let badgeText = tag.tag_type.toUpperCase();
        if (tag.stage_name) {
            badgeText += `: ${tag.stage_name}`;
            if (tag.item_config?.name) {
                badgeText += ` > ${tag.item_config.name}`;
            }
        }

        return (
            <div className={`tag-badge tag-badge-${tag.tag_type}`}>
                {badgeText}
                <button
                    className="remove-tag-btn"
                    onClick={(e) => {
                        e.stopPropagation();
                        handleRemoveTag(tag.column_index);
                    }}
                >
                    ×
                </button>
            </div>
        );
    };

    return (
        <div className="excel-viewer-container">
            <div className="viewer-header">
                <button onClick={onBack} className="back-button">← Back</button>
                <h2>{fileData.filename}</h2>
                <div className="viewer-stats">
                    <span>{fileData.rows} rows</span>
                    <span>{fileData.columns} columns</span>
                    <span>{tags.length} tags</span>
                </div>
            </div>

            {message && (
                <div className={`message ${message.type}`}>
                    {message.text}
                </div>
            )}

            <div className="controls-panel">
                <div className="control-group">
                    <label htmlFor="data-start-row">
                        Data starts from row (0-indexed):
                    </label>
                    <input
                        id="data-start-row"
                        type="number"
                        value={dataStartRow}
                        onChange={(e) => setDataStartRow(parseInt(e.target.value) || 0)}
                        min="0"
                        max={fileData.rows - 1}
                    />
                    <small>Rows before this will be treated as headers for tagging</small>
                </div>

                <div className="action-buttons">
                    <button
                        onClick={handleSaveMapping}
                        disabled={saving || tags.length === 0}
                        className="save-button"
                    >
                        {saving ? 'Saving...' : 'Save Mapping'}
                    </button>
                    <button
                        onClick={handleExtractAndCreate}
                        disabled={extracting || tags.length === 0}
                        className="extract-button"
                    >
                        {extracting ? 'Extracting...' : 'Extract & Create Dashboard'}
                    </button>
                </div>
            </div>

            <div className="tags-summary">
                <h3>Tagged Columns:</h3>
                {tags.length === 0 ? (
                    <p className="no-tags">No columns tagged yet. Click on header cells to start tagging.</p>
                ) : (
                    <div className="tags-list">
                        {tags.map((tag, index) => (
                            <div key={index} className="tag-item">
                                <span className="tag-column">Column {tag.column_index}: {tag.column_name}</span>
                                {renderTagBadge(tag)}
                            </div>
                        ))}
                    </div>
                )}
            </div>

            <div className="excel-table-wrapper">
                <table className="excel-table">
                    <tbody>
                        {fileData.data.map((row, rowIndex) => (
                            <tr key={rowIndex}>
                                <td className="row-number">{rowIndex}</td>
                                {row.map((cell, colIndex) => {
                                    const tag = getColumnTag(colIndex);
                                    return (
                                        <td
                                            key={colIndex}
                                            className={getCellClassName(rowIndex, colIndex)}
                                            onClick={() => handleCellClick(rowIndex, colIndex)}
                                            title={tag ? `Tagged as: ${tag.tag_type}${tag.stage_name ? ` - ${tag.stage_name}` : ''}` : 'Click to tag'}
                                        >
                                            <div className="cell-content">
                                                {cell !== null && cell !== undefined && cell !== '' ? String(cell) : ''}
                                                {tag && rowIndex === 0 && renderTagBadge(tag)}
                                            </div>
                                        </td>
                                    );
                                })}
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {showTagModal && selectedCell && (
                <TaggingModal
                    columnIndex={selectedCell.col}
                    columnName={String(fileData.data[selectedCell.row][selectedCell.col] || `Column ${selectedCell.col}`)}
                    existingTag={getColumnTag(selectedCell.col)}
                    usedStages={usedStages}
                    onSave={handleTagSave}
                    onClose={() => {
                        setShowTagModal(false);
                        setSelectedCell(null);
                    }}
                />
            )}
        </div>
    );
};

export default ExcelViewer;
