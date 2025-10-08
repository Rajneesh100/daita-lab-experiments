import React from 'react';

const StatsCards = ({ stats }) => {
    const formatCurrency = (amount) => {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD'
        }).format(amount || 0);
    };

    return (
        <div className="stats-cards">
            <div className="stat-card">
                <h3>Total Orders</h3>
                <p className="stat-value">{stats.total_orders || 0}</p>
            </div>

            <div className="stat-card">
                <h3>Total Items</h3>
                <p className="stat-value">{stats.total_items || 0}</p>
            </div>

            <div className="stat-card">
                <h3>Total Value</h3>
                <p className="stat-value">{formatCurrency(stats.total_value)}</p>
            </div>

            <div className="stat-card">
                <h3>Total Buyers</h3>
                <p className="stat-value">{stats.total_buyers || 0}</p>
            </div>
        </div>
    );
};

export default StatsCards;
