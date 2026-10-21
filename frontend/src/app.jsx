import { BrowserRouter, Routes, Route } from 'react-router-dom';
import StatPage from './components/StatPage';
import SelectPage from './components/SelectPage';
import AssistantPage from './components/AssistantPage';
import ShortlistPage from './components/ShortlistPage';
import LeagueSummaryPage from './components/LeagueSummaryPage';

function App() {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/" element={<SelectPage />} />
                <Route path="/player/:playerId" element={<StatPage />} />
                <Route path="/assistant" element={<AssistantPage />} />
                <Route path="/ShortlistPage" element={<ShortlistPage />} />
                <Route path="/league-summary" element={<LeagueSummaryPage />} />
            </Routes>
        </BrowserRouter>
    );
}

export default App;
