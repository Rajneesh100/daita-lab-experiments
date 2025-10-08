import React, { useState } from 'react';
import './TaggingModal.css';

interface TaggingModalProps {
    columnIndex: number;
    columnName: string;
    existingTag?: any;
    usedStages: string[];
    onSave: (tagData: any) => void;
    onClose: () => void;
}

const TaggingModal: React.FC<TaggingModalProps> = ({
    columnIndex,
    columnName,
    existingTag,
    usedStages,
    onSave,
    onClose
}) => {
    const [tagType, setTagType] = useState<string>(existingTag?.tag_type || '');

    // Stage configuration
    const [stageName, setStageName] = useState<string>(existingTag?.stage_name || '');
    const [customStageName, setCustomStageName] = useState<string>('');
    const [useCustomStageName, setUseCustomStageName] = useState(false);
    const [stageStartDate, setStageStartDate] = useState<string>(existingTag?.stage_config?.start_date || '');
    const [stageDeadline, setStageDeadline] = useState<string>(existingTag?.stage_config?.deadline || '');
    const [stageExpectedDelivery, setStageExpectedDelivery] = useState<string>(existingTag?.stage_config?.expected_delivery_date || '');
    const [stageManager, setStageManager] = useState<string>(existingTag?.stage_config?.manager || '');
    const [stageTopManager, setStageTopManager] = useState<string>(existingTag?.stage_config?.top_manager || '');
    const [stageParameterName, setStageParameterName] = useState<string>(existingTag?.stage_config?.parameter_name || columnName);

    // Item configuration
    const [hasItem, setHasItem] = useState<boolean>(!!existingTag?.item_config?.name);
    const [itemName, setItemName] = useState<string>(existingTag?.item_config?.name || '');
    const [customItemName, setCustomItemName] = useState<string>('');
    const [useCustomItemName, setUseCustomItemName] = useState(false);
    const [isPlannedDate, setIsPlannedDate] = useState<boolean>(existingTag?.item_config?.is_planned_date || false);
    const [itemStartDate, setItemStartDate] = useState<string>(existingTag?.item_config?.start_date || '');
    const [itemEndDate, setItemEndDate] = useState<string>(existingTag?.item_config?.end_date || '');
    const [itemStatus, setItemStatus] = useState<string>(existingTag?.item_config?.status || 'ongoing');
    const [itemContact, setItemContact] = useState<string>(existingTag?.item_config?.contact || '');

    const [error, setError] = useState<string>('');

    // Get last 2 used stages for suggestions
    const suggestedStages = usedStages.slice(-2);

    const handleSave = () => {
        setError('');

        // Validation for identifier tags
        if (['io', 'style', 'color'].includes(tagType)) {
            const tagData = {
                column_index: columnIndex,
                column_name: columnName,
                tag_type: tagType
            };
            onSave(tagData);
            return;
        }

        // Validation for stage/item tags
        if (!stageName && !customStageName) {
            setError('Stage name is required');
            return;
        }

        const finalStageName = useCustomStageName ? customStageName : stageName;

        if (!finalStageName) {
            setError('Please provide a stage name');
            return;
        }

        // If item is added, validate item fields
        if (hasItem) {
            const finalItemName = useCustomItemName ? customItemName : itemName;
            if (!finalItemName) {
                setError('Item name is required when adding an item');
                return;
            }
            if (!isPlannedDate && !itemStartDate) {
                setError('Either mark as planned date or provide start date for item');
                return;
            }
        }

        // Build stage config
        const stageConfig: any = {
            parameter_name: stageParameterName
        };

        if (stageStartDate) stageConfig.start_date = stageStartDate;
        if (stageDeadline) stageConfig.deadline = stageDeadline;
        if (stageExpectedDelivery) stageConfig.expected_delivery_date = stageExpectedDelivery;
        if (stageManager) stageConfig.manager = stageManager;
        if (stageTopManager) stageConfig.top_manager = stageTopManager;

        // Build item config if item is added
        let itemConfig: any = null;
        if (hasItem) {
            const finalItemName = useCustomItemName ? customItemName : itemName;
            itemConfig = {
                name: finalItemName,
                is_planned_date: isPlannedDate
            };

            if (itemStartDate) itemConfig.start_date = itemStartDate;
            if (itemEndDate) itemConfig.end_date = itemEndDate;
            if (itemStatus) itemConfig.status = itemStatus;
            if (itemContact) itemConfig.contact = itemContact;
        }

        const tagData = {
            column_index: columnIndex,
            column_name: columnName,
            tag_type: hasItem ? 'item' : 'stage',
            stage_name: finalStageName,
            stage_config: stageConfig,
            item_config: itemConfig
        };

        onSave(tagData);
    };

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                <div className="modal-header">
                    <h2>Tag Column: {columnName}</h2>
                    <button className="close-button" onClick={onClose}>×</button>
                </div>

                <div className="modal-body">
                    {error && <div className="error-message">{error}</div>}

                    {/* Tag Type Selection */}
                    <div className="form-section">
                        <h3>Select Tag Type</h3>
                        <div className="tag-type-buttons">
                            <button
                                className={`tag-type-btn ${tagType === 'io' ? 'active' : ''}`}
                                onClick={() => setTagType('io')}
                            >
                                IO (Internal Order)
                            </button>
                            <button
                                className={`tag-type-btn ${tagType === 'style' ? 'active' : ''}`}
                                onClick={() => setTagType('style')}
                            >
                                Style
                            </button>
                            <button
                                className={`tag-type-btn ${tagType === 'color' ? 'active' : ''}`}
                                onClick={() => setTagType('color')}
                            >
                                Color
                            </button>
                            <button
                                className={`tag-type-btn ${['stage', 'item'].includes(tagType) ? 'active' : ''}`}
                                onClick={() => setTagType('stage')}
                            >
                                Stage / Item
                            </button>
                        </div>
                    </div>

                    {/* Stage/Item Configuration */}
                    {['stage', 'item'].includes(tagType) && (
                        <>
                            {/* Stage Configuration */}
                            <div className="form-section">
                                <h3>Stage Configuration <span className="required">*</span></h3>

                                <div className="form-group">
                                    <label>Stage Name <span className="required">*</span></label>

                                    {suggestedStages.length > 0 && !useCustomStageName && (
                                        <div className="suggestions">
                                            <small>Recent stages:</small>
                                            {suggestedStages.map((stage, idx) => (
                                                <button
                                                    key={idx}
                                                    className="suggestion-btn"
                                                    onClick={() => setStageName(stage)}
                                                >
                                                    {stage}
                                                </button>
                                            ))}
                                        </div>
                                    )}

                                    {!useCustomStageName ? (
                                        <>
                                            <select
                                                value={stageName}
                                                onChange={(e) => setStageName(e.target.value)}
                                            >
                                                <option value="">Select or use column name</option>
                                                <option value={columnName}>Use column name: {columnName}</option>
                                                {suggestedStages.map((stage, idx) => (
                                                    <option key={idx} value={stage}>{stage}</option>
                                                ))}
                                            </select>
                                            <button
                                                className="toggle-custom-btn"
                                                onClick={() => setUseCustomStageName(true)}
                                            >
                                                Enter custom name
                                            </button>
                                        </>
                                    ) : (
                                        <>
                                            <input
                                                type="text"
                                                value={customStageName}
                                                onChange={(e) => setCustomStageName(e.target.value)}
                                                placeholder="Enter custom stage name"
                                            />
                                            <button
                                                className="toggle-custom-btn"
                                                onClick={() => setUseCustomStageName(false)}
                                            >
                                                Select from list
                                            </button>
                                        </>
                                    )}
                                </div>

                                <div className="form-row">
                                    <div className="form-group">
                                        <label>Start Date (Optional)</label>
                                        <input
                                            type="text"
                                            value={stageStartDate}
                                            onChange={(e) => setStageStartDate(e.target.value)}
                                            placeholder="YYYY-MM-DD"
                                        />
                                    </div>

                                    <div className="form-group">
                                        <label>Deadline (Optional)</label>
                                        <input
                                            type="text"
                                            value={stageDeadline}
                                            onChange={(e) => setStageDeadline(e.target.value)}
                                            placeholder="YYYY-MM-DD"
                                        />
                                    </div>
                                </div>

                                <div className="form-group">
                                    <label>Expected Delivery Date (Optional)</label>
                                    <input
                                        type="text"
                                        value={stageExpectedDelivery}
                                        onChange={(e) => setStageExpectedDelivery(e.target.value)}
                                        placeholder="YYYY-MM-DD"
                                    />
                                </div>

                                <div className="form-group">
                                    <label>Parameter Name (for stage-level data)</label>
                                    <input
                                        type="text"
                                        value={stageParameterName}
                                        onChange={(e) => setStageParameterName(e.target.value)}
                                        placeholder="Parameter name"
                                    />
                                    <small>This will store column values as stage parameters</small>
                                </div>

                                <div className="form-row">
                                    <div className="form-group">
                                        <label>Manager (Optional)</label>
                                        <input
                                            type="text"
                                            value={stageManager}
                                            onChange={(e) => setStageManager(e.target.value)}
                                            placeholder="Manager name"
                                        />
                                    </div>

                                    <div className="form-group">
                                        <label>Top Manager (Optional)</label>
                                        <input
                                            type="text"
                                            value={stageTopManager}
                                            onChange={(e) => setStageTopManager(e.target.value)}
                                            placeholder="Top manager name"
                                        />
                                    </div>
                                </div>
                            </div>

                            {/* Item Configuration */}
                            <div className="form-section">
                                <h3>
                                    <label className="checkbox-label">
                                        <input
                                            type="checkbox"
                                            checked={hasItem}
                                            onChange={(e) => setHasItem(e.target.checked)}
                                        />
                                        Add Item (Optional)
                                    </label>
                                </h3>

                                {hasItem && (
                                    <>
                                        <div className="form-group">
                                            <label>Item Name <span className="required">*</span></label>

                                            {!useCustomItemName ? (
                                                <>
                                                    <select
                                                        value={itemName}
                                                        onChange={(e) => setItemName(e.target.value)}
                                                    >
                                                        <option value="">Select or use column name</option>
                                                        <option value={columnName}>Use column name: {columnName}</option>
                                                    </select>
                                                    <button
                                                        className="toggle-custom-btn"
                                                        onClick={() => setUseCustomItemName(true)}
                                                    >
                                                        Enter custom name
                                                    </button>
                                                </>
                                            ) : (
                                                <>
                                                    <input
                                                        type="text"
                                                        value={customItemName}
                                                        onChange={(e) => setCustomItemName(e.target.value)}
                                                        placeholder="Enter custom item name"
                                                    />
                                                    <button
                                                        className="toggle-custom-btn"
                                                        onClick={() => setUseCustomItemName(false)}
                                                    >
                                                        Use column name
                                                    </button>
                                                </>
                                            )}
                                        </div>

                                        <div className="form-group">
                                            <label className="checkbox-label">
                                                <input
                                                    type="checkbox"
                                                    checked={isPlannedDate}
                                                    onChange={(e) => setIsPlannedDate(e.target.checked)}
                                                />
                                                This column contains planned dates <span className="required">*</span>
                                            </label>
                                            <small>Check this if column values are dates for this item</small>
                                        </div>

                                        {!isPlannedDate && (
                                            <div className="form-row">
                                                <div className="form-group">
                                                    <label>Start Date</label>
                                                    <input
                                                        type="text"
                                                        value={itemStartDate}
                                                        onChange={(e) => setItemStartDate(e.target.value)}
                                                        placeholder="YYYY-MM-DD"
                                                    />
                                                </div>

                                                <div className="form-group">
                                                    <label>End Date</label>
                                                    <input
                                                        type="text"
                                                        value={itemEndDate}
                                                        onChange={(e) => setItemEndDate(e.target.value)}
                                                        placeholder="YYYY-MM-DD"
                                                    />
                                                </div>
                                            </div>
                                        )}

                                        <div className="form-row">
                                            <div className="form-group">
                                                <label>Status</label>
                                                <select
                                                    value={itemStatus}
                                                    onChange={(e) => setItemStatus(e.target.value)}
                                                >
                                                    <option value="ongoing">Ongoing</option>
                                                    <option value="completed">Completed</option>
                                                    <option value="pending">Pending</option>
                                                    <option value="delayed">Delayed</option>
                                                </select>
                                            </div>

                                            <div className="form-group">
                                                <label>Contact</label>
                                                <input
                                                    type="text"
                                                    value={itemContact}
                                                    onChange={(e) => setItemContact(e.target.value)}
                                                    placeholder="Contact person"
                                                />
                                            </div>
                                        </div>
                                    </>
                                )}
                            </div>
                        </>
                    )}
                </div>

                <div className="modal-footer">
                    <button className="cancel-btn" onClick={onClose}>
                        Cancel
                    </button>
                    <button className="save-btn" onClick={handleSave}>
                        Save Tag
                    </button>
                </div>
            </div>
        </div>
    );
};

export default TaggingModal;
