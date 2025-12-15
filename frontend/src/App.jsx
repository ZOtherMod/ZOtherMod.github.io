import { useState } from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Header from './components/Header'
import Footer from './components/Footer'
import Home from './pages/Home'
import About from './pages/About'
import Login from './pages/Login'
import Debate from './pages/Debate'
import Matchmaking from './pages/Matchmaking'
import Start from './pages/Start'
import End from './pages/End'
import './App.css'

function App() {
  return (
    <Router>
      <div className="App">
        <Header />
        <main>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/about" element={<About />} />
            <Route path="/login" element={<Login />} />
            <Route path="/debate" element={<Debate />} />
            <Route path="/matchmaking" element={<Matchmaking />} />
            <Route path="/start" element={<Start />} />
            <Route path="/end" element={<End />} />
          </Routes>
        </main>
        <Footer />
      </div>
    </Router>
  )
}

export default App