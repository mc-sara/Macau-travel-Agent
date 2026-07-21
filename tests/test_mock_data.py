from agent.mock_data import data_path, load_excel_preview, load_merchants, project_root


def test_project_root_points_to_demo_directory():
    root = project_root()
    assert root.name in {'macau-local-agent-demo', 'Macau-travel-Agent-upload', 'Macau-travel-Agent'}
    assert (root / 'data').exists()


def test_data_path_returns_existing_mock_merchants_file():
    path = data_path('mock_merchants.json')
    assert path.exists()
    assert path.name == 'mock_merchants.json'


def test_load_merchants_returns_required_categories():
    merchants = load_merchants()
    for key in ['senior_activities', 'restaurants', 'drink_shops', 'gift_shops']:
        assert key in merchants
        assert isinstance(merchants[key], list)


def test_load_excel_preview_reads_rows():
    rows = load_excel_preview('macau_attractions.xlsx', max_rows=3)
    assert isinstance(rows, list)
    assert len(rows) <= 3
