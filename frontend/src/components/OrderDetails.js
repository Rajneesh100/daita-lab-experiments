import React, { useState, useEffect } from 'react';
import { useParams, Link, useLocation } from 'react-router-dom';
import axios from 'axios';
import Pagination from './Pagination';

const API_BASE = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

const OrderDetails = () => {
    const { orderId } = useParams();
    const location = useLocation();
    const [orderData, setOrderData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [pagination, setPagination] = useState({
        page: 1,
        limit: 10,
        total: 0,
        total_pages: 0
    });

    // Get filters from URL params (passed from dashboard)
    const getFiltersFromUrl = () => {
        const searchParams = new URLSearchParams(location.search);
        return {
            model_id: searchParams.get('model_id') || '',
            color: searchParams.get('color') || '',
            size: searchParams.get('size') || ''
        };
    };

    const [filters, setFilters] = useState(getFiltersFromUrl());

    const fetchOrderDetails = async () => {
        setLoading(true);
        try {
            const params = new URLSearchParams({
                page: pagination.page,
                limit: pagination.limit,
                ...(filters.model_id && { model_id: filters.model_id }),
                ...(filters.color && { color: filters.color }),
                ...(filters.size && { size: filters.size })
            });

            const response = await axios.get(`${API_BASE}/orders/${orderId}?${params}`);
            setOrderData(response.data);
            setPagination({
                ...pagination,
                total: response.data.pagination.total,
                total_pages: response.data.pagination.total_pages
            });
        } catch (error) {
            setError('Failed to fetch order details');
            console.error('Error fetching order details:', error);
        } finally {
            setLoading(false);
        }
    };

    const handlePageChange = (newPage) => {
        setPagination({ ...pagination, page: newPage });
    };

    useEffect(() => {
        fetchOrderDetails();
    }, [orderId, pagination.page, filters]);

    const formatDate = (dateString) => {
        if (!dateString) return 'N/A';
        return new Date(dateString).toLocaleDateString();
    };

    const formatCurrency = (amount) => {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD'
        }).format(amount || 0);
    };

    if (loading) return <div className="loading">Loading order details...</div>;
    if (error) return <div className="error">{error}</div>;
    if (!orderData) return <div className="error">Order not found</div>;

    const { order, line_items, pagination: paginationData } = orderData;

    return (
        <div className="order-details">
            <div className="order-details-container">
                <div className="order-header">
                    <Link to="/" className="back-btn">← Back to Dashboard</Link>
                    <h1>Order Details - {order.purchase_order_id}</h1>
                </div>

                <div className="order-info">
                    <div className="info-section">
                        <h2>Order Information</h2>
                        <div className="info-grid">
                            <div className="info-item">
                                <label>Purchase Order ID:</label>
                                <span>{order.purchase_order_id}</span>
                            </div>
                            <div className="info-item">
                                <label>Order Date:</label>
                                <span>{formatDate(order.order_date)}</span>
                            </div>
                            <div className="info-item">
                                <label>Currency:</label>
                                <span>{order.currency}</span>
                            </div>
                            <div className="info-item">
                                <label>Total Amount:</label>
                                <span>{formatCurrency(order.total_amount)}</span>
                            </div>
                            <div className="info-item">
                                <label>Tax Amount:</label>
                                <span>{formatCurrency(order.tax_amount)}</span>
                            </div>
                        </div>
                    </div>

                    <div className="info-section">
                        <h2>Buyer Information</h2>
                        <div className="info-item">
                            <label>Name:</label>
                            <span>{order.buyer_name}</span>
                        </div>
                        <div className="info-item">
                            <label>Address:</label>
                            <span className="address">{order.buyer_address}</span>
                        </div>
                    </div>

                    <div className="info-section">
                        <h2>Supplier Information</h2>
                        <div className="info-item">
                            <label>Name:</label>
                            <span>{order.supplier_name || 'N/A'}</span>
                        </div>
                        <div className="info-item">
                            <label>Address:</label>
                            <span className="address">{order.supplier_address || 'N/A'}</span>
                        </div>
                    </div>
                </div>

                <div className="line-items-section">
                    <div className="line-items-header">
                        <h2>Line Items ({paginationData.total} total)</h2>
                        {(filters.model_id || filters.color || filters.size) && (
                            <div className="active-filters">
                                <strong>Active filters:</strong>
                                {filters.model_id && <span className="filter-tag">Model: {filters.model_id}</span>}
                                {filters.color && <span className="filter-tag">Color: {filters.color}</span>}
                                {filters.size && <span className="filter-tag">Size: {filters.size}</span>}
                            </div>
                        )}
                    </div>
                    <div className="line-items-table">
                        <div className="table-header">
                            <div className="table-row header-row">
                                <div className="table-cell">Model ID</div>
                                <div className="table-cell">Description</div>
                                <div className="table-cell">Color</div>
                                <div className="table-cell">Size</div>
                                <div className="table-cell">Quantity</div>
                                <div className="table-cell">Unit Price</div>
                                <div className="table-cell">Amount</div>
                                <div className="table-cell">Delivery Date</div>
                            </div>
                        </div>

                        <div className="table-body">
                            {line_items.map(item => (
                                <div key={item.id} className="table-row">
                                    <div className="table-cell">{item.model_id}</div>
                                    <div className="table-cell">{item.description}</div>
                                    <div className="table-cell">{item.color}</div>
                                    <div className="table-cell">{item.size}</div>
                                    <div className="table-cell">{item.quantity}</div>
                                    <div className="table-cell">{formatCurrency(item.unit_price)}</div>
                                    <div className="table-cell">{formatCurrency(item.amount)}</div>
                                    <div className="table-cell">{formatDate(item.delivery_date)}</div>
                                </div>
                            ))}
                        </div>
                    </div>

                    {paginationData.total_pages > 1 && (
                        <Pagination
                            currentPage={pagination.page}
                            totalPages={paginationData.total_pages}
                            total={paginationData.total}
                            onPageChange={handlePageChange}
                        />
                    )}
                </div>
            </div>
        </div>
    );
};

export default OrderDetails;
