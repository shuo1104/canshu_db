import { NavLink, Route, Routes } from 'react-router-dom'
import { Home, Upload } from 'lucide-react'
import { ImportPage } from './pages/ImportPage'
import { SearchPage } from './pages/SearchPage'

function App() {
  return (
    <>
      <nav className="nav">
        <NavLink to="/" className="nav__brand" end>
          <img src="/logo.png" alt="" />
        </NavLink>
        <div className="nav__links">
          <NavLink
            to="/"
            end
            className={({ isActive }) =>
              `nav__link ${isActive ? 'nav__link--active' : ''}`
            }
          >
            <Home size={16} />
            搜索
          </NavLink>
          <NavLink
            to="/import"
            className={({ isActive }) =>
              `nav__link ${isActive ? 'nav__link--active' : ''}`
            }
          >
            <Upload size={16} />
            数据导入
          </NavLink>
        </div>
      </nav>
      <Routes>
        <Route path="/" element={<SearchPage />} />
        <Route path="/import" element={<ImportPage />} />
      </Routes>
    </>
  )
}

export default App
