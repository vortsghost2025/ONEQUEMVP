# OneQueue Code Review Action Plan

## Priority Matrix

### P0 - Critical (Fix Immediately)
1. **Hardcoded Windows Disk Path** - `monitor.py:29`
2. **Resource Metrics Timing** - `worker.py:76-78`
3. **No API Key Validation** - `nvidia_api.py`

### P1 - High (Fix Before Production)
4. **Duplicate Model Detection** - `worker.py:30-41`
5. **Status String vs Enum** - Multiple files
6. **No Connection Pooling** - `ollama.py`, `nvidia_api.py`
7. **Missing Input Sanitization** - `smart_router.py`

### P2 - Medium (Fix Soon)
8. **Inconsistent Error Messages**
9. **No Rate Limiting**
10. **Database Session in Loop** - `worker.py:133`
11. **Memory Leak in Benchmarks** - `smart_router.py:49`
12. **Missing Type Hints**

### P3 - Low (Nice to Have)
13. **Environment Variable Expansion**
14. **CORS Configuration**
15. **Logger Name Consistency**
16. **Test Coverage**

---

## Implementation Plan

### Phase 1: Critical Fixes (Today)
- [ ] Fix disk path cross-platform compatibility
- [ ] Move resource metrics capture to during execution
- [ ] Add API key validation at startup

### Phase 2: High Priority (This Week)
- [ ] Consolidate model detection logic
- [ ] Standardize status enum usage
- [ ] Implement HTTP connection pooling
- [ ] Add input sanitization

### Phase 3: Medium Priority (Next Week)
- [ ] Standardize error messages
- [ ] Add rate limiting middleware
- [ ] Optimize database sessions
- [ ] Fix memory leak in benchmarks
- [ ] Add type hints

### Phase 4: Low Priority (Backlog)
- [ ] Environment variable expansion
- [ ] Configurable CORS
- [ ] Logger consolidation
- [ ] Test coverage improvement

---

## Status Tracking

### Completed
- [x] Code review documented
- [x] Action plan created

### In Progress
- [ ] P0 fixes

### Pending
- [ ] P1 fixes
- [ ] P2 fixes
- [ ] P3 improvements

---

## Files Requiring Changes

| File | Issues | Priority |
|------|--------|----------|
| `app/monitor.py` | 1, 12 | P0 |
| `app/worker.py` | 2, 4, 5, 10 | P0, P1 |
| `app/services/nvidia_api.py` | 3, 6 | P0, P1 |
| `app/services/ollama.py` | 6 | P1 |
| `app/services/smart_router.py` | 7, 11, 12 | P1, P2 |
| `app/main.py` | 14, 15 | P3 |
| `app/config.py` | 13 | P3 |

---

## Testing Strategy

### Before Each Fix
1. Identify current behavior
2. Write test case
3. Document expected behavior

### After Each Fix
1. Verify fix resolves issue
2. Run existing tests
3. Check for regressions
4. Update documentation

---

## Rollback Plan

If any fix causes issues:
1. Revert commit
2. Document issue
3. Create bug ticket
4. Fix in next iteration

---

**Status**: Ready to begin P0 fixes  
**Timeline**: 1-2 days for P0, 1 week for P1, 2 weeks for P2  
**Risk**: Low (changes are isolated and well-defined)
