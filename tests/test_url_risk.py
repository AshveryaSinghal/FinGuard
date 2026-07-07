from app.url_risk import extract_features, FEATURE_NAMES, url_readiness
def test_feature_contract_and_token_matching():
    f=extract_features('https://paytm.com')
    assert list(f)==FEATURE_NAMES
    assert f['suspicious_term_count']==0
    assert extract_features('https://example.com/pay/login')['suspicious_term_count']==2
def test_url_model_is_never_marked_accepted():
    assert url_readiness()['accepted'] is False
