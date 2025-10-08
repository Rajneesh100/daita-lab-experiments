import React, { useState, useEffect } from 'react';
import axios from 'axios';
import OrdersList from './OrdersList';
import Filters from './Filters';
import StatsCards from './StatsCards';
import Pagination from './Pagination';

const API_BASE = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

const Dashboard = () => {
    const [orders, setOrders] = useState([]);
    const [stats, setStats] = useState({});
    const [filters, setFilters] = useState({
        search: '',
        model_id: '',
        color: '',
        size: ''
    });
    const [pagination, setPagination] = useState({
        page: 1,
        limit: 5,
        total: 0,
        total_pages: 0
    });
    const [sorting, setSorting] = useState({
        sort_by: 'order_date',
        sort_order: 'desc'
    });
    const [loading, setLoading] = useState(false);
    const [filterOptions, setFilterOptions] = useState({
        model_ids: [],
        colors: [],
        sizes: []
    });

    // Fetch orders with current filters and pagination
    const fetchOrders = async () => {
        setLoading(true);
        try {
            const params = new URLSearchParams({
                page: pagination.page,
                limit: pagination.limit,
                sort_by: sorting.sort_by,
                sort_order: sorting.sort_order,
                ...(filters.search && { search: filters.search }),
                ...(filters.model_id && { model_id: filters.model_id }),
                ...(filters.color && { color: filters.color }),
                ...(filters.size && { size: filters.size })
            });

            const response = await axios.get(`${API_BASE}/orders?${params}`);
            setOrders(response.data.orders);
            setPagination({
                ...pagination,
                total: response.data.total,
                total_pages: response.data.total_pages
            });
        } catch (error) {
            console.error('Error fetching orders:', error);
        } finally {
            setLoading(false);
        }
    };

    // Fetch stats
    const fetchStats = async () => {
        try {
            const response = await axios.get(`${API_BASE}/stats`);
            setStats(response.data);
        } catch (error) {
            console.error('Error fetching stats:', error);
        }
    };

    // Fetch filter options
    const fetchFilterOptions = async () => {
        try {
            const response = await axios.get(`${API_BASE}/filters`);
            setFilterOptions(response.data);
        } catch (error) {
            console.error('Error fetching filter options:', error);
        }
    };

    // Handle filter changes
    const handleFilterChange = (newFilters) => {
        setFilters(newFilters);
        setPagination({ ...pagination, page: 1 }); // Reset to first page
    };

    // Handle page changes
    const handlePageChange = (newPage) => {
        setPagination({ ...pagination, page: newPage });
    };

    // Handle page size changes
    const handlePageSizeChange = (newLimit) => {
        setPagination({ ...pagination, limit: newLimit, page: 1 });
    };

    // Handle sorting changes
    const handleSortChange = (sortBy) => {
        const newSortOrder = sorting.sort_by === sortBy && sorting.sort_order === 'desc' ? 'asc' : 'desc';
        setSorting({ sort_by: sortBy, sort_order: newSortOrder });
        setPagination({ ...pagination, page: 1 }); // Reset to first page
    };

    // Fetch data on component mount and when filters/pagination/sorting change
    useEffect(() => {
        fetchOrders();
    }, [filters, pagination.page, pagination.limit, sorting]);

    useEffect(() => {
        fetchStats();
        fetchFilterOptions();
    }, []);

    return (
        <div className="dashboard">
            <div className="dashboard-container">
                <StatsCards stats={stats} />

                <Filters
                    filters={filters}
                    filterOptions={filterOptions}
                    onFilterChange={handleFilterChange}
                />

                <div className="orders-controls">
                    <div className="page-size-control">
                        <label>Show:</label>
                        <select
                            value={pagination.limit}
                            onChange={(e) => handlePageSizeChange(parseInt(e.target.value))}
                            className="page-size-select"
                        >
                            <option value={5}>5 orders</option>
                            <option value={10}>10 orders</option>
                            <option value={20}>20 orders</option>
                            <option value={50}>50 orders</option>
                        </select>
                    </div>

                    <div className="sort-controls">
                        <label>Sort by:</label>
                        <button
                            onClick={() => handleSortChange('order_date')}
                            className={`sort-btn ${sorting.sort_by === 'order_date' ? 'active' : ''}`}
                        >
                            Order Date {sorting.sort_by === 'order_date' && (sorting.sort_order === 'desc' ? '↓' : '↑')}
                        </button>
                        <button
                            onClick={() => handleSortChange('total_amount')}
                            className={`sort-btn ${sorting.sort_by === 'total_amount' ? 'active' : ''}`}
                        >
                            Total Amount {sorting.sort_by === 'total_amount' && (sorting.sort_order === 'desc' ? '↓' : '↑')}
                        </button>
                        <button
                            onClick={() => handleSortChange('item_count')}
                            className={`sort-btn ${sorting.sort_by === 'item_count' ? 'active' : ''}`}
                        >
                            Items Count {sorting.sort_by === 'item_count' && (sorting.sort_order === 'desc' ? '↓' : '↑')}
                        </button>
                    </div>
                </div>

                {loading ? (
                    <div className="loading">Loading orders...</div>
                ) : (
                    <>
                        <OrdersList orders={orders} filters={filters} />

                        <Pagination
                            currentPage={pagination.page}
                            totalPages={pagination.total_pages}
                            total={pagination.total}
                            onPageChange={handlePageChange}
                        />
                    </>
                )}
            </div>
        </div>
    );
};

export default Dashboard;
