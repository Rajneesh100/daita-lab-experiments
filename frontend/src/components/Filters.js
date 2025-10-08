import React from 'react';

const Filters = ({ filters, filterOptions, onFilterChange }) => {
    const handleInputChange = (field, value) => {
        onFilterChange({
            ...filters,
            [field]: value
        });
    };

    const clearFilters = () => {
        onFilterChange({
            search: '',
            model_id: '',
            color: '',
            size: ''
        });
    };

    return (
        <div className="filters">
            <div className="filters-row">
                <div className="filter-group">
                    <label>Search</label>
                    <input
                        type="text"
                        placeholder="Search by PO ID, buyer, or supplier..."
                        value={filters.search}
                        onChange={(e) => handleInputChange('search', e.target.value)}
                        className="filter-input"
                    />
                </div>

                <div className="filter-group">
                    <label>Model ID</label>
                    <select
                        value={filters.model_id}
                        onChange={(e) => handleInputChange('model_id', e.target.value)}
                        className="filter-select"
                    >
                        <option value="">All Models</option>
                        {filterOptions.model_ids.map(model => (
                            <option key={model} value={model}>{model}</option>
                        ))}
                    </select>
                </div>

                <div className="filter-group">
                    <label>Color</label>
                    <select
                        value={filters.color}
                        onChange={(e) => handleInputChange('color', e.target.value)}
                        className="filter-select"
                    >
                        <option value="">All Colors</option>
                        {filterOptions.colors.map(color => (
                            <option key={color} value={color}>{color}</option>
                        ))}
                    </select>
                </div>

                <div className="filter-group">
                    <label>Size</label>
                    <select
                        value={filters.size}
                        onChange={(e) => handleInputChange('size', e.target.value)}
                        className="filter-select"
                    >
                        <option value="">All Sizes</option>
                        {filterOptions.sizes.map(size => (
                            <option key={size} value={size}>{size}</option>
                        ))}
                    </select>
                </div>

                <div className="filter-group">
                    <button onClick={clearFilters} className="clear-btn">
                        Clear Filters
                    </button>
                </div>
            </div>
        </div>
    );
};

export default Filters;
