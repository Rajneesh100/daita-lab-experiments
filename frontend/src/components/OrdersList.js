import React from 'react';
import { Link } from 'react-router-dom';

const OrdersList = ({ orders, filters }) => {
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

    if (orders.length === 0) {
        return (
            <div className="no-orders">
                <p>No orders found.</p>
            </div>
        );
    }

    return (
        <div className="orders-list">
            <div className="orders-table">
                <div className="table-header">
                    <div className="table-row header-row">
                        <div className="table-cell">PO ID</div>
                        <div className="table-cell">Order Date</div>
                        <div className="table-cell">Buyer</div>
                        <div className="table-cell">Total Amount</div>
                        <div className="table-cell">Items</div>
                        <div className="table-cell">Matching Items</div>
                        <div className="table-cell">Actions</div>
                    </div>
                </div>

                <div className="table-body">
                    {orders.map(order => (
                        <div key={order.id} className="table-row">
                            <div className="table-cell">
                                <strong>{order.purchase_order_id}</strong>
                            </div>
                            <div className="table-cell">
                                {formatDate(order.order_date)}
                            </div>
                            <div className="table-cell">
                                {order.buyer_name}
                            </div>
                            <div className="table-cell">
                                {formatCurrency(order.total_amount)}
                            </div>
                            <div className="table-cell">
                                {order.item_count}
                            </div>
                            <div className="table-cell">
                                <span className="match-count">{order.item_match_count || order.item_count}</span>
                            </div>
                            <div className="table-cell">
                                <Link
                                    to={`/orders/${order.id}?${new URLSearchParams({
                                        ...(filters?.model_id && { model_id: filters.model_id }),
                                        ...(filters?.color && { color: filters.color }),
                                        ...(filters?.size && { size: filters.size })
                                    }).toString()}`}
                                    className="view-btn"
                                >
                                    View Details
                                </Link>
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Show matching items preview for each order */}
            {orders.map(order => (
                order.items && order.items.length > 0 && (
                    <div key={`items-${order.id}`} className="order-items-preview">
                        <h4>Matching Items for PO {order.purchase_order_id}:</h4>
                        <div className="items-grid">
                            {order.items.slice(0, 3).map(item => (
                                <div key={item.id} className="item-card">
                                    <div className="item-model">{item.model_id}</div>
                                    <div className="item-desc">{item.description}</div>
                                    <div className="item-details">
                                        <span className="item-color">{item.color}</span>
                                        <span className="item-size">{item.size}</span>
                                        <span className="item-qty">Qty: {item.quantity}</span>
                                    </div>
                                </div>
                            ))}
                            {order.items.length > 3 && (
                                <div className="more-items">
                                    +{order.items.length - 3} more items
                                </div>
                            )}
                        </div>
                    </div>
                )
            ))}
        </div>
    );
};

export default OrdersList;
