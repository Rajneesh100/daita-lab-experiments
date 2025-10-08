import React from 'react';
import { Link } from 'react-router-dom';

const Header = () => {
    return (
        <header className="header">
            <div className="header-container">
                <h1 className="header-title">
                    <Link to="/">Purchase Order Dashboard</Link>
                </h1>
                <nav className="header-nav">
                    <Link to="/" className="nav-link">Dashboard</Link>
                    <Link to="/upload" className="nav-link">Upload PDF</Link>
                </nav>
            </div>
        </header>
    );
};

export default Header;
