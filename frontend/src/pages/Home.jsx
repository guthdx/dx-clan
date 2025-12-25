import { useState, useEffect, useRef, useCallback } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import './Home.css'

// Icons
const SearchIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
    <circle cx="11" cy="11" r="8"/>
    <path d="M21 21l-4.35-4.35"/>
  </svg>
)

const ClockIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <circle cx="12" cy="12" r="10"/>
    <path d="M12 6v6l4 2"/>
  </svg>
)

const TreeIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M12 22V12M12 12L8 8M12 12L16 8M12 8V2M8 8L4 4M16 8L20 4"/>
  </svg>
)

const UsersIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
    <circle cx="9" cy="7" r="4"/>
    <path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>
  </svg>
)

const RECENT_SEARCHES_KEY = 'dx-clan-recent-searches'
const MAX_RECENT = 5

function Home() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [recentPersons, setRecentPersons] = useState([])
  const [recentSearches, setRecentSearches] = useState([])
  const [showDropdown, setShowDropdown] = useState(false)
  const [selectedIndex, setSelectedIndex] = useState(-1)
  const [stats, setStats] = useState(null)

  const searchRef = useRef(null)
  const dropdownRef = useRef(null)
  const navigate = useNavigate()

  // Load recent searches from localStorage
  useEffect(() => {
    const saved = localStorage.getItem(RECENT_SEARCHES_KEY)
    if (saved) {
      try {
        setRecentSearches(JSON.parse(saved))
      } catch (e) {
        console.error('Failed to parse recent searches:', e)
      }
    }
  }, [])

  // Save recent search
  const saveRecentSearch = useCallback((searchQuery, person) => {
    const newRecent = {
      query: searchQuery,
      person: person ? { id: person.id, displayName: person.displayName } : null,
      timestamp: Date.now()
    }

    setRecentSearches(prev => {
      const filtered = prev.filter(r =>
        r.query.toLowerCase() !== searchQuery.toLowerCase()
      )
      const updated = [newRecent, ...filtered].slice(0, MAX_RECENT)
      localStorage.setItem(RECENT_SEARCHES_KEY, JSON.stringify(updated))
      return updated
    })
  }, [])

  // Debounced search
  useEffect(() => {
    if (query.length < 2) {
      setResults([])
      setSelectedIndex(-1)
      return
    }

    const timer = setTimeout(async () => {
      setLoading(true)
      setError(null)
      try {
        const response = await api.searchPersons(query, 10)
        setResults(response.results || [])
        setSelectedIndex(-1)
      } catch (err) {
        setError('Search failed. Please try again.')
        console.error('Search error:', err)
      } finally {
        setLoading(false)
      }
    }, 200)

    return () => clearTimeout(timer)
  }, [query])

  // Load initial data
  useEffect(() => {
    async function loadData() {
      try {
        const [persons, statsData] = await Promise.all([
          api.listPersons(12, 0),
          api.listPersons(1, 0).then(() => ({ total: 13059 })).catch(() => null)
        ])
        setRecentPersons(persons)
        setStats(statsData)
      } catch (err) {
        console.error('Failed to load data:', err)
      }
    }
    loadData()
  }, [])

  // Handle click outside to close dropdown
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (searchRef.current && !searchRef.current.contains(e.target)) {
        setShowDropdown(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Keyboard navigation
  const handleKeyDown = (e) => {
    const items = results.length > 0 ? results : []

    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setSelectedIndex(prev => Math.min(prev + 1, items.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setSelectedIndex(prev => Math.max(prev - 1, -1))
    } else if (e.key === 'Enter' && selectedIndex >= 0 && items[selectedIndex]) {
      e.preventDefault()
      const person = items[selectedIndex]
      saveRecentSearch(query, person)
      navigate(`/person/${person.id}`)
    } else if (e.key === 'Escape') {
      setShowDropdown(false)
    }
  }

  const handleResultClick = (person) => {
    saveRecentSearch(query, person)
    setShowDropdown(false)
  }

  const displayResults = results.length > 0 ? results : []
  const showSuggestions = showDropdown && (query.length >= 2 || recentSearches.length > 0)

  return (
    <div className="home">
      {/* Hero Section */}
      <section className="hero animate-fade-in">
        <div className="hero-crest">
          <img src="/family_crest.png" alt="Duchesneau Family Crest" className="crest-image" />
        </div>
        <div className="hero-content">
          <h2 className="hero-title">Explore Your Roots</h2>
          <p className="hero-subtitle">
            Discover connections across generations in the Ducheneaux family tree
          </p>
        </div>

        {/* Stats */}
        {stats && (
          <div className="stats-row">
            <div className="stat-item">
              <UsersIcon />
              <span className="stat-value">13,000+</span>
              <span className="stat-label">Family Members</span>
            </div>
            <div className="stat-item">
              <TreeIcon />
              <span className="stat-value">7+</span>
              <span className="stat-label">Generations</span>
            </div>
          </div>
        )}
      </section>

      {/* Search Section */}
      <section className="search-section animate-fade-in stagger-1" ref={searchRef}>
        <div className="search-container">
          <div className="search-input-wrapper">
            <SearchIcon />
            <input
              type="text"
              placeholder="Search by name..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onFocus={() => setShowDropdown(true)}
              onKeyDown={handleKeyDown}
              className="search-input"
              aria-label="Search family members"
              autoComplete="off"
            />
            {loading && <div className="search-spinner" />}
          </div>

          {/* Dropdown */}
          {showSuggestions && (
            <div className="search-dropdown" ref={dropdownRef}>
              {/* Recent searches when no query */}
              {query.length < 2 && recentSearches.length > 0 && (
                <div className="dropdown-section">
                  <div className="dropdown-header">
                    <ClockIcon />
                    <span>Recent Searches</span>
                  </div>
                  {recentSearches.map((recent, i) => (
                    <Link
                      key={i}
                      to={recent.person ? `/person/${recent.person.id}` : '#'}
                      className="dropdown-item recent-item"
                      onClick={() => {
                        if (recent.person) {
                          setShowDropdown(false)
                        } else {
                          setQuery(recent.query)
                        }
                      }}
                    >
                      <span className="item-name">
                        {recent.person?.displayName || recent.query}
                      </span>
                    </Link>
                  ))}
                </div>
              )}

              {/* Search results */}
              {query.length >= 2 && (
                <div className="dropdown-section">
                  {displayResults.length > 0 ? (
                    <>
                      <div className="dropdown-header">
                        <span>Results</span>
                        <span className="results-count">{displayResults.length} found</span>
                      </div>
                      {displayResults.map((person, i) => (
                        <Link
                          key={person.id}
                          to={`/person/${person.id}`}
                          className={`dropdown-item ${i === selectedIndex ? 'selected' : ''}`}
                          onClick={() => handleResultClick(person)}
                        >
                          <span className="item-name">{person.displayName}</span>
                          {person.lifespan && (
                            <span className="item-dates">{person.lifespan}</span>
                          )}
                        </Link>
                      ))}
                    </>
                  ) : !loading && (
                    <div className="dropdown-empty">
                      No results for "{query}"
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        {error && <div className="error-message">{error}</div>}
      </section>

      {/* Browse Section */}
      {!query && recentPersons.length > 0 && (
        <section className="browse-section animate-fade-in stagger-2">
          <h2 className="section-title">Browse Family Members</h2>
          <div className="person-grid">
            {recentPersons.map((person, i) => (
              <Link
                key={person.id}
                to={`/person/${person.id}`}
                className={`person-card animate-fade-in stagger-${Math.min(i + 1, 5)}`}
              >
                <div className="card-avatar">
                  {person.displayName.charAt(0).toUpperCase()}
                </div>
                <div className="card-content">
                  <span className="card-name">{person.displayName}</span>
                  {person.lifespan && (
                    <span className="card-dates">{person.lifespan}</span>
                  )}
                </div>
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* Info Section */}
      <section className="info-section animate-fade-in stagger-3">
        <div className="info-card">
          <TreeIcon />
          <h3>Family Tree Visualization</h3>
          <p>
            Click on any family member to view their relationships, then explore
            the interactive family tree to see ancestors and descendants.
          </p>
        </div>
      </section>
    </div>
  )
}

export default Home
