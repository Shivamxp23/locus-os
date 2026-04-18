import React, { useState, useEffect } from 'react';
import { MagnifyingGlass, Lightning, ArrowDown, FunnelSimple, Plus } from '@phosphor-icons/react';
import { useApp } from '../context/AppContext';
import { api } from '../utils/api';
import { getFactionColor, getFactionDimColor, getFactionLabel } from '../utils/helpers';
import './Vault.css';

const FACTIONS = ['health', 'leverage', 'craft', 'expression'];

export default function VaultScreen() {
  useApp();
  const [query, setQuery] = useState('');
  const [searching, setSearching] = useState(false);
  const [results, setResults] = useState(null);
  const [captures, setCaptures] = useState([]);

  useEffect(() => {
    loadCaptures();
  }, []);

  const loadCaptures = async () => {
    const res = await api.getCaptures(false, 10);
    if (res?.captures) setCaptures(res.captures);
  };

  const handleSearch = async () => {
    if (!query.trim()) return;
    setSearching(true);
    let res = await api.searchVault(query);
    
    // Fallback to Vector Search if LightRAG fails or is indexing
    if (!res || !res.results || res.results.length === 0 || res.message) {
      console.log("LightRAG search yielded no direct results, trying Vector search...");
      const vecRes = await api.searchVector(query);
      if (vecRes && vecRes.results) {
        // Map Qdrant result structure to match UI expectations
        res = {
          results: vecRes.results.map(r => ({
            title: r.payload?.title || r.payload?.name || 'Vault Note',
            excerpt: r.payload?.content || 'No preview available',
            score: r.score
          }))
        };
      } else {
        res = { results: [] };
      }
    }
    
    setSearching(false);
    if (res) {
      setResults(res);
    } else {
      setResults({ results: [] });
    }
  };

  return (
    <div className="page-enter">
      <div className="page-container vault-page">
        <header className="vault-header">
          <h1 className="display-l">Vault</h1>
          <p className="body-small text-secondary">
            Your second brain · <span className="text-success">● synced</span>
          </p>
        </header>

        {/* Search bar */}
        <div className="vault-search">
          <MagnifyingGlass size={20} className="vault-search-icon" />
          <input
            className="vault-search-input"
            type="text"
            placeholder="Search your second brain..."
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSearch()}
          />
        </div>

        {/* Quick action chips */}
        <div className="vault-actions">
          <button className="btn-secondary vault-action-chip">
            <Lightning size={14} /> Ask Locus ✦
          </button>
          <button className="btn-secondary vault-action-chip">
            <ArrowDown size={14} /> Recent
          </button>
          <button className="btn-secondary vault-action-chip">
            <FunnelSimple size={14} /> By Faction
          </button>
        </div>

        {/* Search results */}
        {searching && (
          <div className="vault-searching">
            {[1, 2, 3].map(i => (
              <div key={i} className="skeleton" style={{ height: 60, marginBottom: 8 }} />
            ))}
          </div>
        )}

        {results && !searching && (
          <div className="vault-results">
            <h3 className="heading-3 text-tertiary">SEARCH RESULTS</h3>
            {results.results?.length > 0 ? (
              results.results.map((r, i) => (
                <div key={i} className="vault-result-card card">
                  <h4 className="heading-2">{r.title || 'Untitled'}</h4>
                  <p className="body-small text-secondary">{r.excerpt || r.content?.slice(0, 100)}</p>
                </div>
              ))
            ) : (
              <p className="body-small text-tertiary">No results found.</p>
            )}
          </div>
        )}

        {/* Faction index */}
        <div className="vault-faction-grid">
          {FACTIONS.map(f => (
            <button
              key={f}
              className="vault-faction-card"
              style={{
                background: getFactionDimColor(f),
                borderColor: `${getFactionColor(f)}40`,
              }}
            >
              <div className="vault-faction-dot" style={{ background: getFactionColor(f) }} />
              <span className="heading-3" style={{ color: getFactionColor(f) }}>
                {getFactionLabel(f)}
              </span>
              <span className="caption text-tertiary">Tap to explore</span>
            </button>
          ))}
        </div>

        {/* Recent Captures */}
        <div className="vault-recent">
          <h3 className="heading-3 text-tertiary" style={{ marginBottom: 'var(--space-12)' }}>
            RECENT CAPTURES
          </h3>
          <div className="vault-recent-scroll">
            {captures.length > 0 ? captures.map((c, i) => (
              <div key={i} className="vault-capture-card">
                <p className="body-small" style={{ 
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  display: '-webkit-box',
                  WebkitLineClamp: 3,
                  WebkitBoxOrient: 'vertical',
                }}>
                  {c.text}
                </p>
                <span className="caption text-tertiary">
                  {c.created_at ? new Date(c.created_at).toLocaleDateString() : 'Just now'}
                </span>
              </div>
            )) : (
              <div className="vault-capture-card vault-capture-empty">
                <Plus size={24} color="var(--text-tertiary)" />
                <span className="caption text-tertiary">New Capture</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
