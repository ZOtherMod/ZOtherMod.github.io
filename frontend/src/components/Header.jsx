import React from 'react'
import { Link } from 'react-router-dom'

function Header() {
  return (
    <header className="app-header">
      <nav>
        <Link to="/">Home</Link>
        <Link to="/about">About</Link>
        <Link to="/login">Login</Link>
        <Link to="/matchmaking">Matchmaking</Link>
        <Link to="/debate">Debate</Link>
      </nav>
    </header>
  )
}

export default Header