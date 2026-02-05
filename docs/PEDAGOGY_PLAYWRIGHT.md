# Pedagogy Addendum: Playwright UI Testing Framework

*An extension to the Komorebi pedagogical documentation covering end-to-end UI testing.*

---

## Overview

This addendum documents the Playwright testing framework implementation for the Komorebi React dashboard. It extends the core pedagogy by demonstrating how to apply the "Capture Now, Refine Later" philosophy to **test automation**.

### Why Playwright?

| Feature | Benefit for Komorebi |
|---------|---------------------|
| **Cross-browser testing** | Ensures dashboard works in Chrome, Firefox, Safari |
| **Auto-wait** | Handles async React state updates automatically |
| **Trace viewer** | Debug failed tests with step-by-step replay |
| **Parallel execution** | Fast feedback during development |
| **TypeScript support** | Matches our frontend stack |

---

## Architectural Pattern: Page Object Model

The Playwright implementation uses the **Page Object Model (POM)** pattern—a best practice for maintainable UI tests.

### The Pattern

```
┌─────────────────────────────────────────────────────────────┐
│                    Test Files                               │
│  dashboard.spec.ts                                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  test('should capture chunk', async ({ inboxPage }) │   │
│  │  {                                                   │   │
│  │    await inboxPage.captureChunk('My thought');      │   │
│  │  });                                                 │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                  │
│                          ▼                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Page Objects (fixtures.ts)              │   │
│  │                                                      │   │
│  │  class InboxPage {                                  │   │
│  │    get captureInput() { return locator(...) }       │   │
│  │    async captureChunk(content) { ... }              │   │
│  │  }                                                   │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                  │
│                          ▼                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                  Actual DOM                          │   │
│  │  <input class="inbox-input" />                      │   │
│  │  <button class="inbox-button">📝 Capture</button>   │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Benefits

1. **Abstraction**: Tests don't know about CSS selectors
2. **Reusability**: Multiple tests share the same page interactions
3. **Maintainability**: Change selector in one place when UI changes
4. **Readability**: `inboxPage.captureChunk()` is clearer than raw locators

---

## File Structure

```
frontend/
├── e2e/                          # End-to-end tests
│   ├── fixtures.ts               # Page Objects & test fixtures
│   └── dashboard.spec.ts         # Test specifications
├── playwright.config.ts          # Playwright configuration
└── package.json                  # Test scripts added
```

### Key Files

| File | Purpose |
|------|---------|
| `playwright.config.ts` | Browser setup, base URL, web server config |
| `e2e/fixtures.ts` | Page Object Models and API helpers |
| `e2e/dashboard.spec.ts` | Actual test cases |

---

## Page Object Models

The framework provides four Page Object Models:

### 1. DashboardPage
The main page wrapper for navigation and layout.

```typescript
class DashboardPage {
  // Locators
  get header() { return this.page.locator('header.header h1'); }
  get statsSection() { return this.page.locator('.stats'); }
  get inboxTab() { return this.page.locator('.tabs button', { hasText: '📥 Inbox' }); }
  
  // Actions
  async goto() { await this.page.goto('/'); }
  async switchToInbox() { await this.inboxTab.click(); }
}
```

### 2. InboxPage
Handles the quick capture functionality.

```typescript
class InboxPage {
  get captureInput() { return this.page.locator('.inbox-input'); }
  get captureButton() { return this.page.locator('.inbox-button'); }
  
  async captureChunk(content: string) {
    await this.captureInput.fill(content);
    await this.captureButton.click();
  }
}
```

### 3. ChunkListPage
Manages the "All Chunks" view with filtering.

```typescript
class ChunkListPage {
  get filterButtons() { return this.page.locator('.content .tab'); }
  
  async filterByStatus(status: string) {
    await this.page.locator('.content .tab', { hasText: status }).click();
  }
}
```

### 4. ProjectListPage
Handles project creation and listing.

```typescript
class ProjectListPage {
  get newProjectButton() { return this.page.locator('.inbox-button', { hasText: /New Project/i }); }
  
  async createProject(name: string, description?: string) {
    await this.openCreateForm();
    await this.projectNameInput.fill(name);
    if (description) await this.projectDescriptionInput.fill(description);
    await this.createButton.click();
  }
}
```

---

## Test Categories

The test suite is organized into logical categories:

### 1. Layout Tests
Verify the dashboard structure loads correctly.

```typescript
test.describe('Dashboard Layout', () => {
  test('should display the header with title and subtitle');
  test('should display the stats section with all stat cards');
  test('should display navigation tabs');
  test('should display the footer');
});
```

### 2. Navigation Tests
Verify tab switching works correctly.

```typescript
test.describe('Tab Navigation', () => {
  test('should start with Inbox tab active');
  test('should switch to All Chunks tab');
  test('should switch to Projects tab');
  test('should switch back to Inbox tab');
});
```

### 3. Functionality Tests
Verify user interactions work.

```typescript
test.describe('Inbox Functionality', () => {
  test('should capture a chunk and clear input');
  test('should disable button when input is empty');
});
```

### 4. Integration Tests
Verify frontend-backend integration.

```typescript
test.describe('Integration Tests', () => {
  test('should update stats after capturing a chunk');
  test('should show chunk in All Chunks after capture');
});
```

---

## API Helper

The framework includes an `ApiHelper` class for backend interaction during tests:

```typescript
class ApiHelper {
  async createChunk(content: string, tags: string[] = []): Promise<string>;
  async createProject(name: string, description?: string): Promise<string>;
  async getStats(): Promise<{ inbox: number; processed: number; total: number }>;
}
```

This enables:
- **Test data setup** before UI tests
- **Verification** of backend state after UI actions
- **Cleanup** after tests

---

## Running Tests

### Commands

```bash
cd frontend

# Run all tests (headless)
npm test

# Run with browser visible
npm run test:headed

# Run with Playwright UI (interactive)
npm run test:ui

# Run in debug mode
npm run test:debug

# View HTML report
npm run test:report
```

### Configuration

The `playwright.config.ts` automatically:
1. Starts the backend server on port 8000
2. Starts the frontend dev server on port 3000
3. Runs tests against the live application

```typescript
webServer: [
  {
    command: 'cd .. && python -m cli.main serve',
    url: 'http://localhost:8000/health',
  },
  {
    command: 'npm run dev',
    url: 'http://localhost:3000',
  },
],
```

---

## Lessons Learned

### Lesson 5: Test Pyramid in Practice

The Komorebi test strategy follows the test pyramid:

```
        ▲
       /│\        E2E Tests (Playwright)
      / │ \       - Slow, expensive, high confidence
     /  │  \      - Test critical user journeys
    /───┼───\     
   /    │    \    Integration Tests (pytest API)
  /     │     \   - Medium speed, test API contracts
 /      │      \  
/───────┼───────\ Unit Tests (pytest models)
        │         - Fast, cheap, test logic
        │
```

**Key insight**: Playwright tests are at the top of the pyramid. Use them sparingly for critical paths, not for every edge case.

### Lesson 6: Async-First Testing

React with signals requires async-aware testing:

```typescript
// ❌ Bad: Doesn't wait for React to update
await inboxPage.captureChunk('test');
expect(chunks).toHaveCount(1);

// ✅ Good: Wait for the chunk to appear
await inboxPage.captureChunk('test');
await page.waitForTimeout(500);  // Or use proper wait
await expect(page.locator('.chunk-item')).toHaveCount(1);
```

Playwright's auto-wait helps, but understanding React's async nature is crucial.

### Lesson 7: Test Data Isolation

Each test should be independent:

```typescript
// Use unique identifiers to avoid conflicts
const testContent = `Test chunk ${Date.now()}`;

// Create test-specific data
await api.createChunk(testContent);

// Verify only your data
await expect(page.locator('.chunk-content', { hasText: testContent })).toBeVisible();
```

---

## References

1. [Playwright Documentation](https://playwright.dev/docs/intro)
2. [Page Object Model Pattern](https://playwright.dev/docs/pom)
3. [Playwright Test Fixtures](https://playwright.dev/docs/test-fixtures)
4. [React Testing Best Practices](https://playwright.dev/docs/test-components)

---

## Integration with Test Manifest

The Playwright tests are documented in the [Test Manifest](./TEST_MANIFEST.md) under the automated tests section. The human testing procedures (HT-9: Frontend Dashboard Test) complement these automated tests for scenarios that require human judgment.

---

*This addendum extends the core PEDAGOGY.md with UI testing concepts. For the main pedagogical documentation, see [PEDAGOGY.md](./PEDAGOGY.md).*
