/**
 * Komorebi Dashboard UI Tests
 * 
 * End-to-end tests for the React dashboard using Playwright.
 * These tests verify that the UI components work correctly
 * with a live backend.
 */

import { test, expect } from './fixtures';

test.describe('Dashboard Layout', () => {
  test('should display the header with title and subtitle', async ({ dashboardPage }) => {
    await dashboardPage.goto();
    
    await expect(dashboardPage.header).toBeVisible();
    await expect(dashboardPage.header).toContainText('Komorebi');
    await expect(dashboardPage.subtitle).toContainText('Cognitive Infrastructure Dashboard');
  });

  test('should display the stats section with all stat cards', async ({ dashboardPage }) => {
    await dashboardPage.goto();
    
    await expect(dashboardPage.statsSection).toBeVisible();
    await expect(dashboardPage.statCards).toHaveCount(5);
  });

  test('should display navigation tabs', async ({ dashboardPage }) => {
    await dashboardPage.goto();
    
    await expect(dashboardPage.inboxTab).toBeVisible();
    await expect(dashboardPage.allChunksTab).toBeVisible();
    await expect(dashboardPage.projectsTab).toBeVisible();
  });

  test('should display the footer', async ({ dashboardPage }) => {
    await dashboardPage.goto();
    
    await expect(dashboardPage.footer).toBeVisible();
    await expect(dashboardPage.footer).toContainText('Komorebi v0.1.0');
    await expect(dashboardPage.footer).toContainText('Capture Now, Refine Later');
  });
});

test.describe('Tab Navigation', () => {
  test('should start with Inbox tab active', async ({ dashboardPage, page }) => {
    await dashboardPage.goto();
    
    // Inbox tab should be active by default
    await expect(dashboardPage.inboxTab).toHaveClass(/active/);
    
    // Should show Quick Capture heading
    await expect(page.locator('h2', { hasText: 'Quick Capture' })).toBeVisible();
  });

  test('should switch to All Chunks tab', async ({ dashboardPage, page }) => {
    await dashboardPage.goto();
    
    await dashboardPage.switchToAllChunks();
    
    await expect(dashboardPage.allChunksTab).toHaveClass(/active/);
    // Should show filter buttons
    await expect(page.locator('.content .tab', { hasText: /all/i })).toBeVisible();
  });

  test('should switch to Projects tab', async ({ dashboardPage, page }) => {
    await dashboardPage.goto();
    
    await dashboardPage.switchToProjects();
    
    await expect(dashboardPage.projectsTab).toHaveClass(/active/);
    // Should show Projects heading or new project button
    await expect(page.locator('h2, .inbox-button').first()).toBeVisible();
  });

  test('should switch back to Inbox tab', async ({ dashboardPage, page }) => {
    await dashboardPage.goto();
    
    // Switch away then back
    await dashboardPage.switchToProjects();
    await dashboardPage.switchToInbox();
    
    await expect(dashboardPage.inboxTab).toHaveClass(/active/);
    await expect(page.locator('h2', { hasText: 'Quick Capture' })).toBeVisible();
  });
});

test.describe('Stats Display', () => {
  test('should display numeric values in stat cards', async ({ dashboardPage }) => {
    await dashboardPage.goto();
    
    // All stat values should be numbers (including 0)
    const statValues = dashboardPage.page.locator('.stat-value');
    const count = await statValues.count();
    
    for (let i = 0; i < count; i++) {
      const text = await statValues.nth(i).textContent();
      expect(text).toMatch(/^\d+$/);
    }
  });

  test('should display correct stat labels', async ({ dashboardPage }) => {
    await dashboardPage.goto();
    
    const labels = dashboardPage.page.locator('.stat-label');
    
    await expect(labels.nth(0)).toContainText('Inbox');
    await expect(labels.nth(1)).toContainText('Processed');
    await expect(labels.nth(2)).toContainText('Compacted');
    await expect(labels.nth(3)).toContainText('Archived');
    await expect(labels.nth(4)).toContainText('Total');
  });
});

test.describe('Inbox Functionality', () => {
  test('should have capture input and button', async ({ dashboardPage, inboxPage }) => {
    await dashboardPage.goto();
    
    await expect(inboxPage.captureInput).toBeVisible();
    await expect(inboxPage.captureButton).toBeVisible();
    await expect(inboxPage.captureInput).toHaveAttribute('placeholder', /capture/i);
  });

  test('should disable button when input is empty', async ({ dashboardPage, inboxPage }) => {
    await dashboardPage.goto();
    
    await expect(inboxPage.captureButton).toBeDisabled();
  });

  test('should enable button when input has content', async ({ dashboardPage, inboxPage }) => {
    await dashboardPage.goto();
    
    await inboxPage.captureInput.fill('Test content');
    
    await expect(inboxPage.captureButton).toBeEnabled();
  });

  test('should capture a chunk and clear input', async ({ dashboardPage, inboxPage, page }) => {
    await dashboardPage.goto();
    
    const testContent = `Playwright test chunk ${Date.now()}`;
    
    await inboxPage.captureChunk(testContent);
    
    // Input should be cleared
    await expect(inboxPage.captureInput).toHaveValue('');
    
    // The new chunk should appear in the list (either inbox or processed)
    await dashboardPage.switchToAllChunks();
    // Use proper wait for element instead of hardcoded timeout
    await expect(page.locator('.chunk-content', { hasText: testContent })).toBeVisible({ timeout: 5000 });
  });

  test('should show empty state when no inbox chunks', async ({ dashboardPage, inboxPage }) => {
    await dashboardPage.goto();
    
    // If inbox is empty, should show empty state
    const hasChunks = await inboxPage.chunkItems.count() > 0;
    
    if (!hasChunks) {
      await expect(inboxPage.emptyState).toBeVisible();
      await expect(inboxPage.emptyState).toContainText('empty');
    }
  });
});

test.describe('Chunk List Functionality', () => {
  test('should display filter buttons', async ({ dashboardPage, chunkListPage }) => {
    await dashboardPage.goto();
    await dashboardPage.switchToAllChunks();
    
    await expect(chunkListPage.filterButtons).toHaveCount(5);
  });

  test('should filter by status', async ({ dashboardPage, chunkListPage, page }) => {
    await dashboardPage.goto();
    await dashboardPage.switchToAllChunks();
    
    // Click on 'all' filter
    await chunkListPage.filterByStatus('all');
    
    // Should show all chunks or empty state
    const hasContent = await page.locator('.chunk-item, .empty-state').count() > 0;
    expect(hasContent).toBe(true);
  });

  test('should highlight active filter button', async ({ dashboardPage, chunkListPage }) => {
    await dashboardPage.goto();
    await dashboardPage.switchToAllChunks();
    
    // Click processed filter
    await chunkListPage.filterByStatus('processed');
    
    const processedButton = chunkListPage.page.locator('.content .tab', { 
      hasText: /processed/i 
    });
    await expect(processedButton).toHaveClass(/active/);
  });
});

test.describe('Project Management', () => {
  test('should display new project button', async ({ dashboardPage, projectListPage }) => {
    await dashboardPage.goto();
    await dashboardPage.switchToProjects();
    
    await expect(projectListPage.newProjectButton).toBeVisible();
  });

  test('should open create project form', async ({ dashboardPage, projectListPage }) => {
    await dashboardPage.goto();
    await dashboardPage.switchToProjects();
    
    await projectListPage.openCreateForm();
    
    await expect(projectListPage.projectNameInput).toBeVisible();
    await expect(projectListPage.projectDescriptionInput).toBeVisible();
    await expect(projectListPage.createButton).toBeVisible();
  });

  test('should close create form on cancel', async ({ dashboardPage, projectListPage }) => {
    await dashboardPage.goto();
    await dashboardPage.switchToProjects();
    
    await projectListPage.openCreateForm();
    await expect(projectListPage.projectNameInput).toBeVisible();
    
    await projectListPage.cancelButton.click();
    
    await expect(projectListPage.projectNameInput).not.toBeVisible();
  });

  test('should create a new project', async ({ dashboardPage, projectListPage, page }) => {
    await dashboardPage.goto();
    await dashboardPage.switchToProjects();
    
    const projectName = `Test Project ${Date.now()}`;
    const projectDescription = 'Created by Playwright test';
    
    await projectListPage.createProject(projectName, projectDescription);
    
    // Wait for the project to appear
    await page.waitForTimeout(500);
    
    // Project should appear in the list
    await expect(page.locator('.project-name', { hasText: projectName })).toBeVisible();
  });

  test('should disable create button when name is empty', async ({ dashboardPage, projectListPage }) => {
    await dashboardPage.goto();
    await dashboardPage.switchToProjects();
    
    await projectListPage.openCreateForm();
    
    // Name is empty, button should be disabled
    await expect(projectListPage.createButton).toBeDisabled();
    
    // Add name, button should be enabled
    await projectListPage.projectNameInput.fill('Test');
    await expect(projectListPage.createButton).toBeEnabled();
  });
});

test.describe('Integration Tests', () => {
  test('should update stats after capturing a chunk', async ({ dashboardPage, inboxPage, api }) => {
    await dashboardPage.goto();
    
    // Get initial total
    const initialStats = await api.getStats();
    const initialTotal = initialStats.total;
    
    // Capture a new chunk
    const testContent = `Stats integration test ${Date.now()}`;
    await inboxPage.captureChunk(testContent);
    
    // Wait for processing and stats refresh
    await dashboardPage.page.waitForTimeout(1000);
    
    // Verify stats increased (may need to refresh the page for stats to update)
    await dashboardPage.page.reload();
    await dashboardPage.page.waitForTimeout(500);
    
    const newTotal = await dashboardPage.getStatValue('Total');
    expect(parseInt(newTotal)).toBeGreaterThanOrEqual(initialTotal + 1);
  });

  test('should show chunk in All Chunks after capture', async ({ dashboardPage, inboxPage, page }) => {
    await dashboardPage.goto();
    
    const testContent = `Cross-tab test ${Date.now()}`;
    
    // Capture in inbox
    await inboxPage.captureChunk(testContent);
    await page.waitForTimeout(500);
    
    // Switch to all chunks
    await dashboardPage.switchToAllChunks();
    
    // Should find the chunk
    await expect(page.locator('.chunk-content', { hasText: testContent })).toBeVisible();
  });
});

test.describe('Accessibility', () => {
  test('should have proper heading structure', async ({ dashboardPage, page }) => {
    await dashboardPage.goto();
    
    // Should have h1
    const h1 = page.locator('h1');
    await expect(h1).toHaveCount(1);
    
    // Should have h2 in content area
    await expect(page.locator('h2').first()).toBeVisible();
  });

  test('should have clickable buttons', async ({ dashboardPage }) => {
    await dashboardPage.goto();
    
    // All tab buttons should be clickable
    await expect(dashboardPage.inboxTab).toBeEnabled();
    await expect(dashboardPage.allChunksTab).toBeEnabled();
    await expect(dashboardPage.projectsTab).toBeEnabled();
  });

  test('should have form inputs with placeholders', async ({ dashboardPage, inboxPage }) => {
    await dashboardPage.goto();
    
    await expect(inboxPage.captureInput).toHaveAttribute('placeholder');
  });
});

test.describe('Error Handling', () => {
  test('should handle empty form submission gracefully', async ({ dashboardPage, inboxPage }) => {
    await dashboardPage.goto();
    
    // Try to click submit with empty input (button should be disabled)
    await expect(inboxPage.captureButton).toBeDisabled();
    
    // No error state should appear
    const errorElements = dashboardPage.page.locator('[class*="error"]');
    await expect(errorElements).toHaveCount(0);
  });
});
