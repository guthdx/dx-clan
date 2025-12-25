import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api } from '../lib/api'
import Loading from '../components/Loading'
import './PersonDetail.css'

function PersonDetail() {
  const { id } = useParams()
  const [person, setPerson] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    async function loadPerson() {
      setLoading(true)
      setError(null)
      try {
        const data = await api.getPerson(id)
        setPerson(data)
      } catch (err) {
        setError('Failed to load person details.')
        console.error('Load error:', err)
      } finally {
        setLoading(false)
      }
    }
    loadPerson()
  }, [id])

  if (loading) {
    return <Loading message="Loading person details..." size="large" />
  }

  if (error || !person) {
    return (
      <div className="error">
        <p>{error || 'Person not found.'}</p>
        <Link to="/">Back to Search</Link>
      </div>
    )
  }

  return (
    <div className="person-detail">
      <nav className="breadcrumb">
        <Link to="/">Home</Link> &gt; <span>{person.displayName}</span>
      </nav>

      <header className="person-header">
        <h1>{person.displayName}</h1>
        {person.lifespan && <p className="lifespan">{person.lifespan}</p>}
        {person.birthYearCirca && <span className="circa">(circa)</span>}
        <Link to={`/person/${person.id}/tree`} className="view-tree-link">
          View Family Tree
        </Link>
      </header>

      <section className="person-info">
        {person.aliases && person.aliases.length > 0 && (
          <div className="info-group">
            <h3>Also Known As</h3>
            <ul className="alias-list">
              {person.aliases.map((alias) => (
                <li key={alias.id}>{alias.aliasName}</li>
              ))}
            </ul>
          </div>
        )}

        {person.generation && (
          <div className="info-group">
            <h3>Generation</h3>
            <p>{person.generation}</p>
          </div>
        )}

        {person.notes && (
          <div className="info-group">
            <h3>Notes</h3>
            <p>{person.notes}</p>
          </div>
        )}
      </section>

      {person.spouses && person.spouses.length > 0 && (
        <section className="relationships">
          <h2>Spouses</h2>
          <ul className="person-list">
            {person.spouses.map((spouse) => (
              <li key={spouse.person.id}>
                <Link to={`/person/${spouse.person.id}`} className="person-link">
                  <span className="person-name">{spouse.person.displayName}</span>
                  {spouse.person.lifespan && (
                    <span className="person-dates">{spouse.person.lifespan}</span>
                  )}
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}

      {person.parents && person.parents.length > 0 && (
        <section className="relationships">
          <h2>Parents</h2>
          <ul className="person-list">
            {person.parents.map((parent) => (
              <li key={parent.id}>
                <Link to={`/person/${parent.id}`} className="person-link">
                  <span className="person-name">{parent.displayName}</span>
                  {parent.lifespan && (
                    <span className="person-dates">{parent.lifespan}</span>
                  )}
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}

      {person.children && person.children.length > 0 && (
        <section className="relationships">
          <h2>Children</h2>
          <ul className="person-list">
            {person.children.map((child) => (
              <li key={child.id}>
                <Link to={`/person/${child.id}`} className="person-link">
                  <span className="person-name">{child.displayName}</span>
                  {child.lifespan && (
                    <span className="person-dates">{child.lifespan}</span>
                  )}
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}

      <footer className="person-footer">
        <Link to="/" className="back-link">← Back to Search</Link>
      </footer>
    </div>
  )
}

export default PersonDetail
