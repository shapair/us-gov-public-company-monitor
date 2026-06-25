import { useEffect, useState } from 'react'
import SummaryCards from './components/SummaryCards'
import EventTypeBreakdown from './components/EventTypeBreakdown'
import ContractsTable from './components/ContractsTable'
import TickerBarChart from './components/TickerBarChart'
import AgencyFilter from './components/AgencyFilter'
import OfficialTradesTable from './components/OfficialTradesTable'
import OfficialTradesChart from './components/OfficialTradesChart'
import OfficialTradesNetChart from './components/OfficialTradesNetChart'
import ChamberFilter from './components/ChamberFilter'
import TransactionTypeFilter from './components/TransactionTypeFilter'
import FederalStakesChart from './components/FederalStakesChart'
import FederalStakesTable from './components/FederalStakesTable'
import StakeTypeFilter from './components/StakeTypeFilter'
import ForeignHoldingsChart from './components/ForeignHoldingsChart'
import ForeignHoldingsByFilerChart from './components/ForeignHoldingsByFilerChart'
import ForeignHoldingsTable from './components/ForeignHoldingsTable'
import FilerFilter from './components/FilerFilter'
import FilingTypeFilter from './components/FilingTypeFilter'
import DataMonitor from './components/DataMonitor'
import PipelineMonitor from './components/PipelineMonitor'
import PortfolioAnalysis from './components/PortfolioAnalysis'

const API_BASE = import.meta.env.VITE_API_BASE || '/api/v1'
const PAGE_LIMIT = 50

const TABS = [
  { id: 'contracts', label: 'Government Contracts' },
  { id: 'trades', label: 'Official Stock Trades' },
  { id: 'stakes', label: 'Federal Direct Stakes' },
  { id: 'foreign-holdings', label: 'Foreign Government Holdings' },
  { id: 'monitor', label: 'Data Monitor' },
  { id: 'pipelines', label: 'Pipeline Monitor' },
  { id: 'portfolio', label: 'Portfolio Analysis' },
]

function App() {
  const [summary, setSummary] = useState(null)
  const [agencies, setAgencies] = useState([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('contracts')

  const [contracts, setContracts] = useState([])
  const [contractsTotal, setContractsTotal] = useState(0)
  const [contractsOffset, setContractsOffset] = useState(0)
  const [chartYear, setChartYear] = useState(2026)
  const [selectedAgencies, setSelectedAgencies] = useState([])

  const [trades, setTrades] = useState([])
  const [tradesTotal, setTradesTotal] = useState(0)
  const [tradesOffset, setTradesOffset] = useState(0)
  const [selectedChambers, setSelectedChambers] = useState([])
  const [selectedTradeTypes, setSelectedTradeTypes] = useState([])
  const [officialFilter, setOfficialFilter] = useState('')
  const [tradeChartMode, setTradeChartMode] = useState('value')

  const [stakes, setStakes] = useState([])
  const [stakesTotal, setStakesTotal] = useState(0)
  const [stakesOffset, setStakesOffset] = useState(0)
  const [stakeAgencies, setStakeAgencies] = useState([])
  const [selectedStakeAgencies, setSelectedStakeAgencies] = useState([])
  const [selectedStakeTypes, setSelectedStakeTypes] = useState([])

  const [holdings, setHoldings] = useState([])
  const [holdingsTotal, setHoldingsTotal] = useState(0)
  const [holdingsOffset, setHoldingsOffset] = useState(0)
  const [holdingFilers, setHoldingFilers] = useState([])
  const [selectedHoldingFilers, setSelectedHoldingFilers] = useState([])
  const [selectedFilingTypes, setSelectedFilingTypes] = useState([])
  const [holdingChartMode, setHoldingChartMode] = useState('ticker')

  const fetchContracts = async (currentOffset, currentAgencies = selectedAgencies) => {
    const params = new URLSearchParams({
      limit: String(PAGE_LIMIT),
      offset: String(currentOffset),
    })
    currentAgencies.forEach((agency) => params.append('agency', agency))
    const res = await fetch(`${API_BASE}/contracts/?${params}`)
    const data = await res.json()
    setContracts(data.items || [])
    setContractsTotal(data.total || 0)
  }

  const fetchStakes = async (
    currentOffset,
    currentAgencies = selectedStakeAgencies,
    currentTypes = selectedStakeTypes
  ) => {
    const params = new URLSearchParams({
      limit: String(PAGE_LIMIT),
      offset: String(currentOffset),
    })
    currentAgencies.forEach((a) => params.append('agency', a))
    currentTypes.forEach((t) => params.append('stake_type', t))
    const res = await fetch(`${API_BASE}/stakes/?${params}`)
    const data = await res.json()
    setStakes(data.items || [])
    setStakesTotal(data.total || 0)
  }

  const fetchHoldings = async (
    currentOffset,
    currentFilers = selectedHoldingFilers,
    currentFilingTypes = selectedFilingTypes
  ) => {
    const params = new URLSearchParams({
      limit: String(PAGE_LIMIT),
      offset: String(currentOffset),
    })
    currentFilers.forEach((f) => params.append('filer', f))
    currentFilingTypes.forEach((t) => params.append('filing_type', t))
    const res = await fetch(`${API_BASE}/foreign-holdings/?${params}`)
    const data = await res.json()
    setHoldings(data.items || [])
    setHoldingsTotal(data.total || 0)
  }

  const fetchTrades = async (
    currentOffset,
    currentChambers = selectedChambers,
    currentTradeTypes = selectedTradeTypes,
    currentOfficial = officialFilter
  ) => {
    const params = new URLSearchParams({
      limit: String(PAGE_LIMIT),
      offset: String(currentOffset),
    })
    currentChambers.forEach((c) => params.append('chamber', c))
    currentTradeTypes.forEach((t) => params.append('transaction_type', t))
    if (currentOfficial) params.set('official', currentOfficial)
    const res = await fetch(`${API_BASE}/trades/?${params}`)
    const data = await res.json()
    setTrades(data.items || [])
    setTradesTotal(data.total || 0)
  }

  useEffect(() => {
    async function loadData() {
      try {
        const [summaryRes, agenciesRes, stakeAgenciesRes, holdingFilersRes] = await Promise.all([
          fetch(`${API_BASE}/dashboard/summary`),
          fetch(`${API_BASE}/contracts/agencies`),
          fetch(`${API_BASE}/stakes/agencies`),
          fetch(`${API_BASE}/foreign-holdings/filers`),
        ])
        const summaryData = await summaryRes.json()
        const agenciesData = await agenciesRes.json()
        const stakeAgenciesData = await stakeAgenciesRes.json()
        const holdingFilersData = await holdingFilersRes.json()
        setSummary(summaryData)
        setAgencies(agenciesData || [])
        setStakeAgencies(stakeAgenciesData || [])
        setHoldingFilers(holdingFilersData || [])
        await fetchContracts(0, [])
      } catch (err) {
        console.error('Failed to load dashboard data', err)
      } finally {
        setLoading(false)
      }
    }
    loadData()
  }, [])

  useEffect(() => {
    if (activeTab !== 'trades') return
    if (trades.length === 0 && tradesTotal === 0 && !loading) {
      fetchTrades(0)
    }
  }, [activeTab, loading])

  useEffect(() => {
    if (activeTab !== 'stakes') return
    if (stakes.length === 0 && stakesTotal === 0 && !loading) {
      fetchStakes(0)
    }
  }, [activeTab, loading])

  useEffect(() => {
    if (activeTab !== 'foreign-holdings') return
    if (holdings.length === 0 && holdingsTotal === 0 && !loading) {
      fetchHoldings(0)
    }
  }, [activeTab, loading])

  const handleAgencyChange = async (nextAgencies) => {
    setSelectedAgencies(nextAgencies)
    setContractsOffset(0)
    setLoading(true)
    try {
      await fetchContracts(0, nextAgencies)
    } catch (err) {
      console.error('Failed to filter by agency', err)
    } finally {
      setLoading(false)
    }
  }

  const handleContractPageChange = async (page) => {
    const newOffset = (page - 1) * PAGE_LIMIT
    setContractsOffset(newOffset)
    setLoading(true)
    try {
      await fetchContracts(newOffset)
    } catch (err) {
      console.error('Failed to load page', err)
    } finally {
      setLoading(false)
    }
  }

  const handleChamberChange = async (nextChambers) => {
    setSelectedChambers(nextChambers)
    setTradesOffset(0)
    setLoading(true)
    try {
      await fetchTrades(0, nextChambers, selectedTradeTypes, officialFilter)
    } catch (err) {
      console.error('Failed to filter trades by chamber', err)
    } finally {
      setLoading(false)
    }
  }

  const handleTradeTypeChange = async (nextTypes) => {
    setSelectedTradeTypes(nextTypes)
    setTradesOffset(0)
    setLoading(true)
    try {
      await fetchTrades(0, selectedChambers, nextTypes, officialFilter)
    } catch (err) {
      console.error('Failed to filter trades by type', err)
    } finally {
      setLoading(false)
    }
  }

  const handleOfficialFilterChange = async (value) => {
    setOfficialFilter(value)
    setTradesOffset(0)
    setLoading(true)
    try {
      await fetchTrades(0, selectedChambers, selectedTradeTypes, value)
    } catch (err) {
      console.error('Failed to filter trades by official', err)
    } finally {
      setLoading(false)
    }
  }

  const handleTradePageChange = async (page) => {
    const newOffset = (page - 1) * PAGE_LIMIT
    setTradesOffset(newOffset)
    setLoading(true)
    try {
      await fetchTrades(newOffset, selectedChambers, selectedTradeTypes, officialFilter)
    } catch (err) {
      console.error('Failed to load trades page', err)
    } finally {
      setLoading(false)
    }
  }

  const handleStakeAgencyChange = async (nextAgencies) => {
    setSelectedStakeAgencies(nextAgencies)
    setStakesOffset(0)
    setLoading(true)
    try {
      await fetchStakes(0, nextAgencies, selectedStakeTypes)
    } catch (err) {
      console.error('Failed to filter stakes by agency', err)
    } finally {
      setLoading(false)
    }
  }

  const handleStakeTypeChange = async (nextTypes) => {
    setSelectedStakeTypes(nextTypes)
    setStakesOffset(0)
    setLoading(true)
    try {
      await fetchStakes(0, selectedStakeAgencies, nextTypes)
    } catch (err) {
      console.error('Failed to filter stakes by type', err)
    } finally {
      setLoading(false)
    }
  }

  const handleStakePageChange = async (page) => {
    const newOffset = (page - 1) * PAGE_LIMIT
    setStakesOffset(newOffset)
    setLoading(true)
    try {
      await fetchStakes(newOffset, selectedStakeAgencies, selectedStakeTypes)
    } catch (err) {
      console.error('Failed to load stakes page', err)
    } finally {
      setLoading(false)
    }
  }

  const handleHoldingFilerChange = async (nextFilers) => {
    setSelectedHoldingFilers(nextFilers)
    setHoldingsOffset(0)
    setLoading(true)
    try {
      await fetchHoldings(0, nextFilers, selectedFilingTypes)
    } catch (err) {
      console.error('Failed to filter holdings by filer', err)
    } finally {
      setLoading(false)
    }
  }

  const handleFilingTypeChange = async (nextTypes) => {
    setSelectedFilingTypes(nextTypes)
    setHoldingsOffset(0)
    setLoading(true)
    try {
      await fetchHoldings(0, selectedHoldingFilers, nextTypes)
    } catch (err) {
      console.error('Failed to filter holdings by filing type', err)
    } finally {
      setLoading(false)
    }
  }

  const handleHoldingPageChange = async (page) => {
    const newOffset = (page - 1) * PAGE_LIMIT
    setHoldingsOffset(newOffset)
    setLoading(true)
    try {
      await fetchHoldings(newOffset, selectedHoldingFilers, selectedFilingTypes)
    } catch (err) {
      console.error('Failed to load holdings page', err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex flex-col">
      {/* Global nav */}
      <header className="bg-apple-black text-white h-11 flex items-center shrink-0">
        <div className="max-w-[1440px] mx-auto w-full px-6 flex items-center justify-between">
          <div className="flex items-center gap-6">
            <span className="font-display text-apple-nav tracking-apple-nav">US Gov Monitor</span>
            <nav className="hidden md:flex items-center gap-5 text-apple-nav tracking-apple-nav text-white/90">
              {TABS.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`hover:text-white transition-colors ${activeTab === tab.id ? 'text-white font-medium' : ''}`}
                >
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>
          <a
            href="https://github.com/VoltAgent/awesome-design-md"
            target="_blank"
            rel="noreferrer"
            className="text-apple-nav tracking-apple-nav text-white/90 hover:text-white no-underline"
          >
            Design
          </a>
        </div>
      </header>

      {/* Frosted sub-nav */}
      <div className="apple-frosted-bar">
        <div className="max-w-[1440px] mx-auto px-6 h-[52px] flex items-center justify-between">
          <h1 className="font-display text-apple-tagline tracking-apple-tagline">
            {TABS.find((t) => t.id === activeTab)?.label}
          </h1>
          <nav className="flex items-center gap-1 md:hidden">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-3 py-1.5 rounded-apple-pill text-apple-caption transition-colors ${
                  activeTab === tab.id
                    ? 'bg-apple-primary text-white'
                    : 'text-apple-ink hover:bg-apple-divider-soft'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </nav>
        </div>
      </div>

      <main className="flex-1 max-w-[1440px] mx-auto w-full px-6 py-6 md:py-8">
        {loading && activeTab !== 'monitor' && contracts.length === 0 && trades.length === 0 && stakes.length === 0 && holdings.length === 0 ? (
          <div className="text-center py-20 text-apple-ink-muted-48 text-apple-body">Loading…</div>
        ) : (
          <>
            {activeTab !== 'monitor' && activeTab !== 'pipelines' && (
              <>
                <SummaryCards summary={summary} />

                <section className="mt-5 md:mt-6">
                  <EventTypeBreakdown by_type={summary.by_type} />
                </section>
              </>
            )}

            {activeTab === 'monitor' && (
              <section className="mt-2 md:mt-4">
                <DataMonitor />
              </section>
            )}

            {activeTab === 'pipelines' && (
              <section className="mt-2 md:mt-4">
                <PipelineMonitor />
              </section>
            )}

            {activeTab === 'portfolio' && (
              <section className="mt-2 md:mt-4">
                <PortfolioAnalysis />
              </section>
            )}

            {activeTab !== 'monitor' && activeTab !== 'pipelines' && activeTab !== 'portfolio' && (
              <>
              <section className="mt-6 md:mt-8">
              <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3">
                <h2 className="apple-section-title">Explore</h2>
                <div className="flex flex-wrap items-center gap-3">
                  {activeTab === 'contracts' && (
                    <>
                      <AgencyFilter
                        agencies={agencies}
                        selected={selectedAgencies}
                        onChange={handleAgencyChange}
                      />
                      <select
                        value={chartYear}
                        onChange={(e) =>
                          setChartYear(e.target.value === 'all' ? 'all' : Number(e.target.value))
                        }
                        className="appearance-none bg-apple-canvas text-apple-ink border border-apple-hairline rounded-apple-pill px-4 py-2 text-apple-caption focus:outline-none focus:ring-2 focus:ring-apple-primary-focus h-[38px]"
                      >
                        <option value={2026}>2026</option>
                        <option value={2025}>2025</option>
                        <option value="all">All years</option>
                      </select>
                    </>
                  )}
                  {activeTab === 'trades' && (
                    <>
                      <ChamberFilter
                        selected={selectedChambers}
                        onChange={handleChamberChange}
                      />
                      <TransactionTypeFilter
                        selected={selectedTradeTypes}
                        onChange={handleTradeTypeChange}
                      />
                      <input
                        type="text"
                        value={officialFilter}
                        onChange={(e) => handleOfficialFilterChange(e.target.value)}
                        placeholder="Search official…"
                        className="bg-apple-canvas text-apple-ink border border-apple-hairline rounded-apple-pill px-4 py-2 text-apple-caption placeholder:text-apple-ink-muted-48 focus:outline-none focus:ring-2 focus:ring-apple-primary-focus h-[38px] min-w-[180px]"
                      />
                    </>
                  )}
                  {activeTab === 'stakes' && (
                    <>
                      <AgencyFilter
                        agencies={stakeAgencies}
                        selected={selectedStakeAgencies}
                        onChange={handleStakeAgencyChange}
                      />
                      <StakeTypeFilter
                        selected={selectedStakeTypes}
                        onChange={handleStakeTypeChange}
                      />
                    </>
                  )}
                  {activeTab === 'foreign-holdings' && (
                    <>
                      <FilerFilter
                        filers={holdingFilers}
                        selected={selectedHoldingFilers}
                        onChange={handleHoldingFilerChange}
                      />
                      <FilingTypeFilter
                        selected={selectedFilingTypes}
                        onChange={handleFilingTypeChange}
                      />
                    </>
                  )}
                </div>
              </div>
            </section>

            {activeTab === 'contracts' && (
              <>
                <section className="mt-6">
                  <h2 className="apple-section-title mb-3">Top Tickers by Contract Value</h2>
                  <TickerBarChart
                    year={chartYear === 'all' ? null : chartYear}
                    agencies={selectedAgencies}
                    limit={20}
                  />
                </section>

                <section className="mt-8">
                  <h2 className="apple-section-title mb-3">Government Contracts / Grants</h2>
                  <ContractsTable
                    contracts={contracts}
                    offset={contractsOffset}
                    limit={PAGE_LIMIT}
                    total={contractsTotal}
                    onPageChange={handleContractPageChange}
                  />
                </section>
              </>
            )}

            {activeTab === 'trades' && (
              <>
                <section className="mt-6">
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-3">
                    <h2 className="apple-section-title">
                      {tradeChartMode === 'value'
                        ? 'Top Tickers by Official Trade Value'
                        : 'Net Purchase vs Sale Flow by Ticker'}
                    </h2>
                    <div className="flex rounded-apple-pill p-1 bg-apple-pearl border border-apple-divider-soft">
                      <button
                        onClick={() => setTradeChartMode('value')}
                        className={`px-4 py-1.5 rounded-apple-pill text-apple-caption transition-all ${
                          tradeChartMode === 'value'
                            ? 'bg-apple-primary text-white'
                            : 'text-apple-ink hover:bg-apple-divider-soft'
                        }`}
                      >
                        Total Value
                      </button>
                      <button
                        onClick={() => setTradeChartMode('net')}
                        className={`px-4 py-1.5 rounded-apple-pill text-apple-caption transition-all ${
                          tradeChartMode === 'net'
                            ? 'bg-apple-primary text-white'
                            : 'text-apple-ink hover:bg-apple-divider-soft'
                        }`}
                      >
                        Net Buy/Sell
                      </button>
                    </div>
                  </div>
                  {tradeChartMode === 'value' ? (
                    <OfficialTradesChart
                      chambers={selectedChambers}
                      transactionTypes={selectedTradeTypes}
                      limit={20}
                    />
                  ) : (
                    <OfficialTradesNetChart chambers={selectedChambers} limit={20} />
                  )}
                </section>

                <section className="mt-8">
                  <h2 className="apple-section-title mb-3">Official Stock Trades</h2>
                  <OfficialTradesTable
                    trades={trades}
                    offset={tradesOffset}
                    limit={PAGE_LIMIT}
                    total={tradesTotal}
                    onPageChange={handleTradePageChange}
                  />
                </section>
              </>
            )}

            {activeTab === 'stakes' && (
              <>
                <section className="mt-6">
                  <h2 className="apple-section-title mb-3">Top Tickers by Federal Stake Amount</h2>
                  <FederalStakesChart agencies={selectedStakeAgencies} limit={20} />
                </section>

                <section className="mt-8">
                  <h2 className="apple-section-title mb-3">Federal Direct Equity Stakes</h2>
                  <FederalStakesTable
                    stakes={stakes}
                    offset={stakesOffset}
                    limit={PAGE_LIMIT}
                    total={stakesTotal}
                    onPageChange={handleStakePageChange}
                  />
                </section>
              </>
            )}

            {activeTab === 'foreign-holdings' && (
              <>
                <section className="mt-6">
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-3">
                    <h2 className="apple-section-title">
                      {holdingChartMode === 'ticker'
                        ? 'Top Tickers by Foreign Holding Value'
                        : 'Top Filers by Total Holding Value'}
                    </h2>
                    <div className="flex rounded-apple-pill p-1 bg-apple-pearl border border-apple-divider-soft">
                      <button
                        onClick={() => setHoldingChartMode('ticker')}
                        className={`px-4 py-1.5 rounded-apple-pill text-apple-caption transition-all ${
                          holdingChartMode === 'ticker'
                            ? 'bg-apple-primary text-white'
                            : 'text-apple-ink hover:bg-apple-divider-soft'
                        }`}
                      >
                        By Ticker
                      </button>
                      <button
                        onClick={() => setHoldingChartMode('filer')}
                        className={`px-4 py-1.5 rounded-apple-pill text-apple-caption transition-all ${
                          holdingChartMode === 'filer'
                            ? 'bg-apple-primary text-white'
                            : 'text-apple-ink hover:bg-apple-divider-soft'
                        }`}
                      >
                        By Filer
                      </button>
                    </div>
                  </div>
                  {holdingChartMode === 'ticker' ? (
                    <ForeignHoldingsChart
                      filers={selectedHoldingFilers}
                      filingTypes={selectedFilingTypes}
                      limit={20}
                    />
                  ) : (
                    <ForeignHoldingsByFilerChart
                      filingTypes={selectedFilingTypes}
                      limit={20}
                    />
                  )}
                </section>

                <section className="mt-8">
                  <h2 className="apple-section-title mb-3">Foreign Government Holdings</h2>
                  <ForeignHoldingsTable
                    holdings={holdings}
                    offset={holdingsOffset}
                    limit={PAGE_LIMIT}
                    total={holdingsTotal}
                    onPageChange={handleHoldingPageChange}
                  />
                </section>
              </>
            )}
            </>
            )}
          </>
        )}
      </main>

      <footer className="bg-apple-parchment border-t border-apple-hairline py-12">
        <div className="max-w-[1440px] mx-auto px-6 text-apple-fine-print text-apple-ink-muted-48">
          US Gov — Public Company Monitor. Built with Apple-style design language.
        </div>
      </footer>
    </div>
  )
}

export default App
