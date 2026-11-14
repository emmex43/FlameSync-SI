import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { useCompare } from '../context/useCompare';
import type { RankingPayload, RankedItem, RankingResponse } from '../types/index';

export default function Ranking() {
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(false);
  const [rankedItems, setRankedItems] = useState<RankedItem[]>([]);
  const [errorMessage, setErrorMessage] = useState('');
  const [hasRunRanking, setHasRunRanking] = useState(false);
  const { selectedInvestigations, toggleInvestigation } = useCompare();

  const [missionScenario, setMissionScenario] = useState('Lunar Habitat');
  const [constraints, setConstraints] = useState('High Oxygen, Microgravity');

  const handleRank = async () => {
    setIsLoading(true);
    try {
      const payload: RankingPayload = {
        mission_scenario: missionScenario,
        constraints: constraints
      };

      const data = await api.post('/rankings', payload) as RankingResponse;
      setRankedItems(data.rankings);
      setErrorMessage('');
      setHasRunRanking(true);
    } catch (err) {
      console.error("Ranking failed:", err);
      setRankedItems([]);
      setErrorMessage('Could not rank records. Check that the backend is running and try again.');
      setHasRunRanking(false);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full max-w-5xl mx-auto font-mono selection:bg-[#FF5500] selection:text-white gap-6 overflow-hidden">

      <div className="shrink-0">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold text-white tracking-[0.2em] uppercase mb-1">
              Dataset Relevance Ranking
            </h1>
            <p className="text-gray-400 text-xs font-sans">
              Rank local NASA records by how their source data matches your mission and constraints.
            </p>
          </div>
          <button
            onClick={() => navigate('/compare')}
            disabled={selectedInvestigations.length === 0}
            className="shrink-0 border border-[#FF5500]/50 text-[#FF5500] hover:bg-[#FF5500]/10 disabled:opacity-30 disabled:cursor-not-allowed px-4 py-2 rounded text-[9px] font-bold tracking-widest uppercase transition-colors"
          >
            Compare selected ({selectedInvestigations.length})
          </button>
        </div>
      </div>

      {/* Configuration Area */}
      <div className="shrink-0 border border-[#1a1a1a] bg-[#050505] p-5 rounded-xl flex gap-4 items-end">
        <div className="flex-1 flex flex-col gap-2">
          <label className="text-[9px] text-gray-500 font-bold tracking-widest uppercase">Mission Scenario</label>
          <select
            value={missionScenario}
            onChange={(e) => setMissionScenario(e.target.value)}
            className="bg-black border border-[#1a1a1a] text-white text-xs p-3 rounded outline-none focus:border-[#FF5500]"
          >
            <option value="Lunar Habitat">Lunar Habitat</option>
            <option value="Mars Rover">Mars Rover</option>
            <option value="ISS Module">ISS Module</option>
          </select>
        </div>
        <div className="flex-1 flex flex-col gap-2">
          <label className="text-[9px] text-gray-500 font-bold tracking-widest uppercase">Constraints / Priority Factors</label>
          <input
            type="text"
            value={constraints}
            onChange={(e) => setConstraints(e.target.value)}
            className="bg-black border border-[#1a1a1a] text-white text-xs p-3 rounded outline-none focus:border-[#FF5500]"
          />
        </div>
        <button
          onClick={handleRank}
          disabled={isLoading}
          className="bg-[#FF5500] hover:bg-[#FF5500]/80 disabled:opacity-50 text-black px-8 py-3 rounded text-[11px] font-bold tracking-widest uppercase transition-colors shrink-0"
        >
          {isLoading ? 'Processing...' : 'Run Ranking'}
        </button>
      </div>

      {/* Results List */}
      <div className="flex-1 overflow-y-auto border border-[#1a1a1a] bg-[#050505] rounded-xl">
        {errorMessage ? (
          <div className="h-full flex items-center justify-center text-xs text-red-400 font-bold tracking-widest uppercase px-6 text-center">
            {errorMessage}
          </div>
        ) : rankedItems.length === 0 ? (
          <div className="h-full flex items-center justify-center text-xs text-gray-600 font-bold tracking-widest uppercase">
            {isLoading
              ? 'Searching local NASA records...'
              : hasRunRanking
                ? 'No dataset rows matched those terms. Try broader keywords.'
                : 'Run a ranking to find matching records.'}
          </div>
        ) : (
          <div className="flex flex-col divide-y divide-[#1a1a1a]">
            {rankedItems.map((item, index) => (
              <div key={item.investigation_id} className="p-6 flex gap-6 items-center hover:bg-[#1a1a1a]/30 transition-colors">

                <div className="text-3xl font-orbitron font-bold text-gray-700 w-8 text-center shrink-0">
                  {index + 1}
                </div>

                <div className="w-56 shrink-0 flex flex-col gap-1">
                  <span className="text-white font-bold tracking-wider">{item.investigation_id}</span>
                  <span className="text-[10px] text-gray-400">{item.investigation.name}</span>
                  <span className="text-[9px] text-gray-600">{item.investigation.source_file} · row {item.investigation.source_row}</span>
                  <span className="text-[10px] text-[#FF5500] font-bold tracking-widest uppercase">Match Score: {item.relevance_score}%</span>
                </div>

                <div className="flex-1 flex flex-col gap-3">
                  {/* Progress Bar */}
                  <div className="h-1.5 bg-black border border-[#1a1a1a] rounded-full overflow-hidden w-full max-w-md">
                    <div
                      className="h-full bg-[#FF5500] transition-all duration-1000"
                      style={{ width: `${item.relevance_score}%` }}
                    />
                  </div>
                  <div className="text-xs text-gray-400 font-sans leading-relaxed">
                    <strong className="text-gray-500 font-mono text-[9px] uppercase tracking-widest mr-2">Top Reason:</strong>
                    {item.reasoning}
                  </div>
                </div>
                <button
                  onClick={() => toggleInvestigation(item.investigation)}
                  disabled={
                    selectedInvestigations.length >= 4 &&
                    !selectedInvestigations.some((selected) => selected.id === item.investigation_id)
                  }
                  className="shrink-0 border border-[#1a1a1a] hover:border-[#FF5500] text-gray-400 hover:text-[#FF5500] disabled:opacity-30 disabled:cursor-not-allowed px-3 py-2 rounded text-[9px] font-bold tracking-widest uppercase transition-colors"
                >
                  {selectedInvestigations.some((selected) => selected.id === item.investigation_id)
                    ? 'Selected'
                    : 'Compare'}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}