/**
 * Playwright test fixtures for Komorebi Dashboard.
 * 
 * Provides reusable test fixtures including:
 * - API helpers for backend interaction
 * - Page object models
 * - Test data utilities
 */

import { test as base, expect, Page } from '@playwright/test';

/**
 * API helper for interacting with the backend during tests.
 */
class ApiHelper {
  private baseUrl = 'http://localhost:8000/api/v1';

  async createChunk(content: string, tags: string[] = []): Promise<string> {
    const response = await fetch(`${this.baseUrl}/chunks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content, tags, source: 'playwright-test' }),
    });
    const data = await response.json();
    return data.id;
  }

  async createProject(name: string, description?: string): Promise<string> {
    const response = await fetch(`${this.baseUrl}/projects`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, description }),
    });
    const data = await response.json();
    return data.id;
  }

  async getStats(): Promise<{ inbox: number; processed: number; total: number }> {
    const response = await fetch(`${this.baseUrl}/chunks/stats`);
    return response.json();
  }

  async clearTestData(): Promise<void> {
    // Note: In a real app, you might have a dedicated test cleanup endpoint
    // For now, we'll just ensure tests are isolated by unique content
  }
}

/**
 * Page Object Model for the Dashboard.
 */
class DashboardPage {
  constructor(private page: Page) {}

  // Locators
  get header() {
    return this.page.locator('header.header h1');
  }

  get subtitle() {
    return this.page.locator('header.header .subtitle');
  }

  get statsSection() {
    return this.page.locator('.stats');
  }

  get statCards() {
    return this.page.locator('.stat-card');
  }

  get inboxTab() {
    return this.page.locator('.tabs button', { hasText: '📥 Inbox' });
  }

  get allChunksTab() {
    return this.page.locator('.tabs button', { hasText: '📋 All Chunks' });
  }

  get projectsTab() {
    return this.page.locator('.tabs button', { hasText: '📁 Projects' });
  }

  get contentArea() {
    return this.page.locator('main.content');
  }

  get footer() {
    return this.page.locator('footer.footer');
  }

  // Actions
  async goto() {
    await this.page.goto('/');
  }

  async switchToInbox() {
    await this.inboxTab.click();
  }

  async switchToAllChunks() {
    await this.allChunksTab.click();
  }

  async switchToProjects() {
    await this.projectsTab.click();
  }

  async getStatValue(label: string): Promise<string> {
    const card = this.page.locator('.stat-card', { hasText: label });
    return card.locator('.stat-value').textContent() || '';
  }
}

/**
 * Page Object Model for the Inbox component.
 */
class InboxPage {
  constructor(private page: Page) {}

  get captureInput() {
    return this.page.locator('.inbox-input');
  }

  get captureButton() {
    return this.page.locator('.inbox-button');
  }

  get chunkList() {
    return this.page.locator('.chunk-list');
  }

  get chunkItems() {
    return this.page.locator('.chunk-item');
  }

  get emptyState() {
    return this.page.locator('.empty-state');
  }

  get loadingState() {
    return this.page.locator('.loading');
  }

  async captureChunk(content: string) {
    await this.captureInput.fill(content);
    await this.captureButton.click();
  }

  async getChunkContent(index: number): Promise<string> {
    const chunk = this.chunkItems.nth(index);
    return chunk.locator('.chunk-content').textContent() || '';
  }
}

/**
 * Page Object Model for the ChunkList component.
 */
class ChunkListPage {
  constructor(private page: Page) {}

  get filterButtons() {
    return this.page.locator('.content .tab');
  }

  get chunkItems() {
    return this.page.locator('.chunk-item');
  }

  get emptyState() {
    return this.page.locator('.empty-state');
  }

  async filterByStatus(status: 'all' | 'inbox' | 'processed' | 'compacted' | 'archived') {
    const button = this.page.locator('.content .tab', { 
      hasText: new RegExp(status, 'i') 
    });
    await button.click();
  }
}

/**
 * Page Object Model for the ProjectList component.
 */
class ProjectListPage {
  constructor(private page: Page) {}

  get newProjectButton() {
    return this.page.locator('.inbox-button', { hasText: /New Project/i });
  }

  get projectNameInput() {
    return this.page.locator('input[placeholder="Project name"]');
  }

  get projectDescriptionInput() {
    return this.page.locator('input[placeholder*="Description"]');
  }

  get createButton() {
    return this.page.locator('button', { hasText: 'Create Project' });
  }

  get cancelButton() {
    return this.page.locator('.inbox-button', { hasText: /Cancel/i });
  }

  get projectCards() {
    return this.page.locator('.project-card');
  }

  get emptyState() {
    return this.page.locator('.empty-state');
  }

  async openCreateForm() {
    await this.newProjectButton.click();
  }

  async createProject(name: string, description?: string) {
    await this.openCreateForm();
    await this.projectNameInput.fill(name);
    if (description) {
      await this.projectDescriptionInput.fill(description);
    }
    await this.createButton.click();
  }
}

// Extended test fixture with page objects
type KomorebiFixtures = {
  api: ApiHelper;
  dashboardPage: DashboardPage;
  inboxPage: InboxPage;
  chunkListPage: ChunkListPage;
  projectListPage: ProjectListPage;
};

export const test = base.extend<KomorebiFixtures>({
  api: async ({}, use) => {
    await use(new ApiHelper());
  },
  dashboardPage: async ({ page }, use) => {
    await use(new DashboardPage(page));
  },
  inboxPage: async ({ page }, use) => {
    await use(new InboxPage(page));
  },
  chunkListPage: async ({ page }, use) => {
    await use(new ChunkListPage(page));
  },
  projectListPage: async ({ page }, use) => {
    await use(new ProjectListPage(page));
  },
});

export { expect };
