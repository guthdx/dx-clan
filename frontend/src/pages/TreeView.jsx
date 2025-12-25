import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api } from '../lib/api'
import FamilyTree from '../components/FamilyTree'
import Loading from '../components/Loading'
import './TreeView.css'

function TreeView() {
  const { id } = useParams()
  const [ancestors, setAncestors] = useState(null)
  const [descendants, setDescendants] = useState(null)
  const [person, setPerson] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [ancestorGens, setAncestorGens] = useState(3)
  const [descendantGens, setDescendantGens] = useState(3)

  useEffect(() => {
    async function loadTree() {
      setLoading(true)
      setError(null)
      try {
        const [ancestorData, descendantData, personData] = await Promise.all([
          api.getAncestors(id, ancestorGens),
          api.getDescendants(id, descendantGens),
          api.getPerson(id)
        ])
        setAncestors(ancestorData)
        setDescendants(descendantData)
        setPerson(personData)
      } catch (err) {
        setError('Failed to load family tree.')
        console.error('Tree load error:', err)
      } finally {
        setLoading(false)
      }
    }
    loadTree()
  }, [id, ancestorGens, descendantGens])

  if (loading) {
    return <Loading message="Loading family tree..." size="large" />
  }

  if (error || !person) {
    return (
      <div className="tree-view error">
        <p>{error || 'Person not found.'}</p>
        <Link to="/">Back to Search</Link>
      </div>
    )
  }

  return (
    <div className="tree-view">
      <nav className="breadcrumb">
        <Link to="/">Home</Link> &gt;{' '}
        <Link to={`/person/${person.id}`}>{person.displayName}</Link> &gt;{' '}
        <span>Family Tree</span>
      </nav>

      <header className="tree-header">
        <h1>Family Tree</h1>
        <h2>{person.displayName}</h2>
        {person.lifespan && <p className="lifespan">{person.lifespan}</p>}
      </header>

      <div className="generation-controls">
        <div className="gen-control">
          <label htmlFor="ancestor-gens">Ancestor Generations:</label>
          <select
            id="ancestor-gens"
            value={ancestorGens}
            onChange={(e) => setAncestorGens(Number(e.target.value))}
          >
            {[1, 2, 3, 4, 5].map((n) => (
              <option key={n} value={n}>{n}</option>
            ))}
          </select>
        </div>
        <div className="gen-control">
          <label htmlFor="descendant-gens">Descendant Generations:</label>
          <select
            id="descendant-gens"
            value={descendantGens}
            onChange={(e) => setDescendantGens(Number(e.target.value))}
          >
            {[1, 2, 3, 4, 5].map((n) => (
              <option key={n} value={n}>{n}</option>
            ))}
          </select>
        </div>
      </div>

      <FamilyTree
        ancestors={ancestors}
        descendants={descendants}
        person={person}
      />

      <footer className="tree-footer">
        <Link to={`/person/${person.id}`} className="back-link">
          ← Back to {person.displayName}
        </Link>
      </footer>
    </div>
  )
}

export default TreeView
