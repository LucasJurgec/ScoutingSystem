import { BrowserRouter, Routes, Route } from 'react-router-dom';
import StatPage from './components/StatPage';
import SelectPage from './components/SelectPage';
import AssistantPage from './components/AssistantPage';

function App() {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/" element={<SelectPage />} />
                <Route path="/player/:playerId" element={<StatPage />} />
                <Route path="/assistant" element={<AssistantPage />} />
            </Routes>
        </BrowserRouter>
    );
}

export default App;
