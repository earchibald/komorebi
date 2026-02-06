/**
 * Regression tests for search and filter bugs fixed in v0.7.0.
 *
 * Bug 1: Signal subscription — ChunkList useMemo read .value inside callback,
 *         so search results never displayed and clear left no results.
 * Bug 2: FilterPanel status dropdown made isSearchActive=true, hiding
 *         ChunkList status tab buttons.
 * Bug 3: Enter key in SearchBar did nothing (no keydown handler).
 *
 * These tests require a live backend + frontend (Playwright webServer config).
 */

import { test, expect } from './fixtures';

test.describe('Search & Filter Regression', () => {

  test.beforeEach(async ({ dashboardPage, apiHelper }) => {
    // Seed a few chunks so we have data to search
    await apiHelper.createChunk('Python async debugging patterns', ['python', 'debug']);
    await apiHelper.createChunk('React signal state management tips', ['react', 'signals']);
    await apiHelper.createChunk('Docker deployment configuration guide', ['docker', 'ops']);

    // Navigate to All Chunks tab
    await dashboardPage.goto();
    await dashboardPage.switchToAllChunks();
    // Wait for chunks to load
    await expect(dashboardPage.contentArea.locator('.chunk-list')).toBeVisible({ timeout: 10000 });
  });

  test('typing in search box and pressing Enter shows filtered results', async ({ page }) => {
    const searchInput = page.locator('.search-input');
    await searchInput.fill('Python');
    await searchInput.press('Enter');

    // Wait for search results to appear
    await expect(page.locator('.search-status.results')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('.result-count')).toContainText('result');

    // Should only show chunks matching "Python"
    const chunkItems = page.locator('.chunk-item');
    const count = await chunkItems.count();
    expect(count).toBeGreaterThan(0);

    // Every visible chunk should contain "Python" (case-insensitive)
    for (let i = 0; i < count; i++) {
      const content = await chunkItems.nth(i).locator('.chunk-content').textContent();
      expect(content?.toLowerCase()).toContain('python');
    }
  });

  test('status filter tabs remain visible when search is active', async ({ page }) => {
    const searchInput = page.locator('.search-input');

    // Status tabs should be visible before search
    const statusTabs = page.locator('button.tab', { hasText: /^(All|Inbox|Processed|Compacted|Archived)$/ });
    await expect(statusTabs.first()).toBeVisible();

    // Activate search
    await searchInput.fill('async');
    await searchInput.press('Enter');
    await expect(page.locator('.search-status.results')).toBeVisible({ timeout: 5000 });

    // Status tabs should STILL be visible (regression: they used to disappear)
    await expect(statusTabs.first()).toBeVisible();
    const tabCount = await statusTabs.count();
    expect(tabCount).toBe(5); // All, Inbox, Processed, Compacted, Archived
  });

  test('clearing search restores all chunks', async ({ page }) => {
    const searchInput = page.locator('.search-input');

    // Count chunks before search
    const initialCount = await page.locator('.chunk-item').count();
    expect(initialCount).toBeGreaterThan(0);

    // Search for something specific
    await searchInput.fill('Docker');
    await searchInput.press('Enter');
    await expect(page.locator('.search-status.results')).toBeVisible({ timeout: 5000 });

    // Hit clear
    await page.locator('.search-clear').click();

    // Should restore all chunks (regression: used to show 0)
    await expect(page.locator('.chunk-item').first()).toBeVisible({ timeout: 5000 });
    const restoredCount = await page.locator('.chunk-item').count();
    expect(restoredCount).toBeGreaterThanOrEqual(initialCount);
  });

  test('expanding filters does not hide status tabs', async ({ page }) => {
    // Click filter toggle to expand
    await page.locator('.filter-toggle').click();
    await expect(page.locator('.filter-content')).toBeVisible();

    // Status tabs should still be visible
    const statusTabs = page.locator('button.tab', { hasText: /^(All|Inbox|Processed|Compacted|Archived)$/ });
    await expect(statusTabs.first()).toBeVisible();
    const tabCount = await statusTabs.count();
    expect(tabCount).toBe(5);
  });

  test('applying and clearing filters properly resets state', async ({ page }) => {
    // Open filters
    await page.locator('.filter-toggle').click();
    await expect(page.locator('.filter-content')).toBeVisible();

    // Set entity type filter
    await page.locator('#filter-entity-type').selectOption('error');

    // Wait for search to fire
    await page.waitForTimeout(500);

    // Clear all filters
    await page.locator('.clear-filters-btn').click();

    // Chunks should be visible again (regression: used to show 0)
    await expect(page.locator('.chunk-item').first()).toBeVisible({ timeout: 5000 });
  });
});
