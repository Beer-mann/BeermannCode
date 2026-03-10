# 🎨 Frontend Agent

**Implementation-Spezialist für UI, Components & User Experience**

---

## 📌 Grundinfo

| Eigenschaft | Wert |
|---|---|
| **Typ** | Implementation |
| **Domain** | Frontend |
| **Modus** | Continuous Loop (Task-gesteuert) |
| **Modelle** | Ollama (Docstrings) + Claude Code + Codex + GitHub Copilot |
| **Scope** | Alle 10 Projekte |
| **Auto-Push** | ✅ JA |
| **WhatsApp** | Stündliche Digest |

---

## 🎯 Rolle & Aufgaben

Der Frontend Agent ist der **UI/Component-Implementierer**. Er:

### Core Tasks

1. **Fix TODOs & FIXMEs** (Frontend-spezifisch)
   - Findet Frontend-TODOs in `.js`, `.ts`, `.jsx`, `.tsx`, `.css`, etc.
   - Liest den Code + Design-Context
   - Fixed das Issue (UI-Bug, Layout-Problem, etc.)
   - Schreibt Tests dafür
   - Committed & Pusht

2. **Write Component Tests**
   - React: Jest + React Testing Library
   - Vue: Jest + Vue Testing Library
   - Angular: Jasmine + Karma
   - Zielt auf 80%+ Coverage
   - Unit-Tests + Integration-Tests

3. **Write JSDoc & Component Docs**
   - JSDoc Comments für Functions/Classes
   - Storybook Stories (falls eingesetzt)
   - Komponent-Props dokumentieren
   - TypeScript Types dokumentieren

4. **Implement UI Components**
   - Neue React Components
   - Custom Hooks
   - State Management (Redux/Zustand/Context)
   - Form Handling
   - Responsive Design

5. **UI Enhancement & Styling**
   - CSS/SCSS/Tailwind Improvements
   - Dark Mode Support
   - Theme Implementation
   - Animation/Transition Polishing

6. **Accessibility Fixes (A11y)**
   - ARIA Labels & Roles
   - Keyboard Navigation
   - Screen Reader Support
   - Color Contrast (WCAG)
   - Focus Management

---

## 🔄 Workflow

```
Task Assigned by Architecture Agent
  ↓
Frontend Agent wacht auf
  ↓
Read Context
  ├─ Project Structure (React/Vue/Angular?)
  ├─ Component Library
  ├─ Style Framework (Tailwind/Material/Bootstrap)
  ├─ State Management
  └─ Testing Framework
  ↓
Determine Task Type
  ├─ "TODO: Fix responsive layout on mobile"
  ├─ "Missing tests for LoginForm component"
  ├─ "New Component: UserProfileCard"
  └─ "A11y: Add ARIA labels to buttons"
  ↓
Model Selection
  ├─ Ollama (mistral) → für JSDoc/Doku
  └─ Claude Code/Codex → für alles andere
  ↓
Implementation
  ├─ Write Component Code
  ├─ Write Component Tests
  ├─ Write JSDoc/Storybook
  ├─ Run Tests Locally
  ├─ Test in Browser (responsive, a11y)
  └─ Check Code Quality (eslint, prettier)
  ↓
Commit & Create PR
  ├─ Git add files
  ├─ Git commit -m "frontend: <task description>"
  └─ GitHub PR (oder direct push)
  ↓
Wait for Review Agent
  ├─ Code Review
  ├─ Test Validation
  ├─ Visual Regression Check (optional)
  └─ Approval/Reject
  ↓
IF approved → Auto-Push to main
IF rejected → Frontend Agent fixes issues
  ↓
Done — Update Status in Architecture Queue
```

---

## 🛠️ Code-Beispiele

### Task 1: Fix Responsive Layout Bug

**Input:**
```
Task: Fix mobile layout on ProductCard component
Type: bug_fix
Priority: high
Device: iPhone 12 (375px width)
```

**Agent Action (React + Tailwind):**
```tsx
// BEFORE (not responsive)
export const ProductCard = ({ product }) => (
  <div className="flex p-8 w-full">
    <img src={product.image} className="w-48 h-48" />
    <div className="ml-8">
      <h2 className="text-4xl">{product.name}</h2>
      <p className="text-2xl">${product.price}</p>
    </div>
  </div>
);

// AFTER (responsive)
export const ProductCard = ({ product }: { product: Product }) => (
  <div className="flex flex-col md:flex-row p-4 md:p-8 w-full gap-4">
    <img 
      src={product.image} 
      alt={product.name}
      className="w-full md:w-48 h-auto md:h-48 object-cover rounded-lg" 
    />
    <div className="flex flex-col justify-between md:ml-4">
      <div>
        <h2 className="text-xl md:text-4xl font-bold">{product.name}</h2>
        <p className="text-lg md:text-2xl text-gray-600 mt-2">
          ${product.price.toFixed(2)}
        </p>
      </div>
      <button 
        className="w-full mt-4 bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded"
        onClick={() => onAddToCart(product.id)}
      >
        Add to Cart
      </button>
    </div>
  </div>
);

// Test
describe('ProductCard', () => {
  it('renders correctly on mobile', () => {
    const { container } = render(<ProductCard product={mockProduct} />);
    expect(container.firstChild).toHaveClass('flex-col');
  });

  it('renders in flex-row on desktop', () => {
    // Use matchMedia mock for md breakpoint
    const { container } = render(<ProductCard product={mockProduct} />);
    // Verify desktop layout would apply
  });

  it('has proper alt text for image', () => {
    render(<ProductCard product={mockProduct} />);
    expect(screen.getByAltText(mockProduct.name)).toBeInTheDocument();
  });
});
```

### Task 2: Implement New Component with Tests

**Input:**
```
Task: Create UserProfileCard component
Type: feature_implementation
Priority: high
Figma Design: https://figma.com/...
Props: user, onEdit, onDelete
```

**Agent Action:**
```tsx
// components/UserProfileCard.tsx
import React from 'react';
import { User } from '@/types';

/**
 * Displays user profile information in a card layout.
 * 
 * @component
 * @example
 * ```tsx
 * <UserProfileCard 
 *   user={currentUser}
 *   onEdit={() => navigate('/edit-profile')}
 *   onDelete={handleDeleteAccount}
 * />
 * ```
 */
export interface UserProfileCardProps {
  /** User object containing profile data */
  user: User;
  /** Callback when edit button is clicked */
  onEdit: () => void;
  /** Callback when delete button is clicked */
  onDelete: () => void;
}

export const UserProfileCard: React.FC<UserProfileCardProps> = ({
  user,
  onEdit,
  onDelete,
}) => {
  return (
    <div className="w-full max-w-md p-6 border border-gray-200 rounded-lg shadow-md">
      {/* Avatar */}
      <div className="flex justify-center mb-4">
        <img
          src={user.avatar_url || '/default-avatar.png'}
          alt={`${user.username}'s avatar`}
          className="w-20 h-20 rounded-full object-cover border-2 border-blue-500"
        />
      </div>

      {/* User Info */}
      <div className="text-center mb-4">
        <h2 className="text-2xl font-bold text-gray-900">{user.username}</h2>
        <p className="text-gray-600">{user.email}</p>
        <p className="text-sm text-gray-500 mt-1">
          Member since {new Date(user.created_at).toLocaleDateString()}
        </p>
      </div>

      {/* Stats */}
      {user.stats && (
        <div className="grid grid-cols-3 gap-4 mb-4 py-4 border-t border-b border-gray-200">
          <div className="text-center">
            <p className="text-2xl font-bold text-blue-600">{user.stats.posts}</p>
            <p className="text-xs text-gray-500">Posts</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-green-600">{user.stats.followers}</p>
            <p className="text-xs text-gray-500">Followers</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-purple-600">{user.stats.following}</p>
            <p className="text-xs text-gray-500">Following</p>
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex gap-3">
        <button
          onClick={onEdit}
          className="flex-1 bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-4 rounded transition-colors"
          aria-label="Edit profile"
        >
          Edit Profile
        </button>
        <button
          onClick={onDelete}
          className="flex-1 bg-red-600 hover:bg-red-700 text-white font-semibold py-2 px-4 rounded transition-colors"
          aria-label="Delete account"
        >
          Delete Account
        </button>
      </div>
    </div>
  );
};

// __tests__/UserProfileCard.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { UserProfileCard } from '../UserProfileCard';
import { User } from '@/types';

const mockUser: User = {
  id: 1,
  username: 'niklas',
  email: 'niklas@example.com',
  avatar_url: 'https://example.com/avatar.jpg',
  created_at: '2025-01-01T00:00:00Z',
  stats: { posts: 42, followers: 100, following: 50 },
};

describe('UserProfileCard', () => {
  it('renders user information correctly', () => {
    render(
      <UserProfileCard 
        user={mockUser} 
        onEdit={jest.fn()} 
        onDelete={jest.fn()} 
      />
    );

    expect(screen.getByText('niklas')).toBeInTheDocument();
    expect(screen.getByText('niklas@example.com')).toBeInTheDocument();
    expect(screen.getByText('42')).toBeInTheDocument(); // posts count
  });

  it('calls onEdit when edit button is clicked', () => {
    const onEdit = jest.fn();
    render(
      <UserProfileCard 
        user={mockUser} 
        onEdit={onEdit} 
        onDelete={jest.fn()} 
      />
    );

    fireEvent.click(screen.getByLabelText('Edit profile'));
    expect(onEdit).toHaveBeenCalledTimes(1);
  });

  it('calls onDelete when delete button is clicked', () => {
    const onDelete = jest.fn();
    render(
      <UserProfileCard 
        user={mockUser} 
        onEdit={jest.fn()} 
        onDelete={onDelete} 
      />
    );

    fireEvent.click(screen.getByLabelText('Delete account'));
    expect(onDelete).toHaveBeenCalledTimes(1);
  });

  it('uses default avatar when user.avatar_url is not provided', () => {
    const userWithoutAvatar = { ...mockUser, avatar_url: null };
    render(
      <UserProfileCard 
        user={userWithoutAvatar} 
        onEdit={jest.fn()} 
        onDelete={jest.fn()} 
      />
    );

    const img = screen.getByAltText(`${mockUser.username}'s avatar`);
    expect(img).toHaveAttribute('src', '/default-avatar.png');
  });
});
```

### Task 3: A11y Fix - Add ARIA Labels

**Input:**
```
Task: Add ARIA labels to navigation buttons
Type: accessibility
Priority: high
WCAG Level: AA
```

**Agent Action:**
```tsx
// BEFORE (not accessible)
<nav>
  <button onClick={() => navigate('/home')}>Home</button>
  <button onClick={() => navigate('/about')}>About</button>
  <button onClick={() => openMenu()}>Menu</button>
</nav>

// AFTER (accessible)
<nav role="navigation" aria-label="Main navigation">
  <button 
    onClick={() => navigate('/home')}
    aria-current={isActive('/home') ? 'page' : undefined}
    className="nav-button"
  >
    Home
  </button>
  <button 
    onClick={() => navigate('/about')}
    aria-current={isActive('/about') ? 'page' : undefined}
    className="nav-button"
  >
    About
  </button>
  <button 
    onClick={() => openMenu()}
    aria-expanded={isMenuOpen}
    aria-controls="dropdown-menu"
    aria-label="Toggle navigation menu"
    className="menu-button"
  >
    <span aria-hidden="true">☰</span>
  </button>
  
  {isMenuOpen && (
    <ul 
      id="dropdown-menu"
      role="menu"
      className="dropdown-menu"
    >
      <li role="none">
        <button role="menuitem">Settings</button>
      </li>
      <li role="none">
        <button role="menuitem">Logout</button>
      </li>
    </ul>
  )}
</nav>

// A11y Test
describe('Navigation A11y', () => {
  it('has proper ARIA labels', () => {
    render(<Navigation />);
    
    expect(screen.getByRole('navigation', { name: /main navigation/i }))
      .toBeInTheDocument();
    expect(screen.getByLabelText(/toggle navigation menu/i))
      .toBeInTheDocument();
  });

  it('marks current page with aria-current', () => {
    render(<Navigation currentPage="home" />);
    
    const homeButton = screen.getByRole('button', { name: /home/i });
    expect(homeButton).toHaveAttribute('aria-current', 'page');
  });
});
```

---

## 📊 Unterstützte Frameworks & Tools

| Framework | Test Framework | Styling | State Management |
|-----------|---|---|---|
| React 18+ | Jest + RTL | Tailwind, CSS Modules | Redux, Zustand, Context |
| Vue 3 | Vitest + VTL | Tailwind, SCSS | Pinia, Vuex |
| Angular 16+ | Jasmine + Karma | Angular Material, SCSS | NgRx, Services |
| Svelte | Vitest + Svelte Testing | Tailwind, SCSS | Svelte Stores |
| Next.js 14+ | Jest + RTL | Tailwind | SWR, TanStack Query |

---

## ✅ Quality Checklist (vor Commit)

Frontend Agent prüft IMMER:

- [ ] Component lädt ohne Fehler
- [ ] Unit-Tests schreiben (wenn Task = fix/feature)
- [ ] Code-Qualität: `eslint`, `prettier`, `stylelint`
- [ ] TypeScript Type-Safety
- [ ] Responsive Design (Mobile/Tablet/Desktop)
- [ ] Accessibility WCAG AA
- [ ] JSDoc/Storybook dokumentiert
- [ ] Tests passen (>80% Coverage)
- [ ] Keine Console-Errors
- [ ] Performance-Check (Lighthouse)
- [ ] Git Commit Message aussagekräftig

Wenn ein Check fehlschlägt → Fix vor Commit.

---

## 🎨 Accessibility Standards

Frontend Agent berücksichtigt WCAG 2.1 AA:

- ✅ Color Contrast Ratio 4.5:1
- ✅ Keyboard Navigation (Tab, Enter, Space)
- ✅ Screen Reader Support (ARIA)
- ✅ Focus Management
- ✅ Semantic HTML
- ✅ Alt Text for Images
- ✅ Form Labels
- ✅ Error Messages Clear

---

## 📢 WhatsApp Digest (Stündlich)

```
🎨 *Frontend Update — 16:00*

✅ *Completed (letzte Stunde):*
• ProductCard — Fixed responsive layout (high)
• LoginForm — Added 8 unit tests (coverage: 87%)
• Navigation — A11y labels added (WCAG AA)

⏳ *In Progress:*
• UserProfileCard component
• Dark mode toggle implementation

📋 *Pending:*
• Fix 4 TODOs in BeermannBot
• Storybook docs for 3 components

⚠️ *Issues:*
Keine.
```

---

## 🚀 Performance Optimization

Frontend Agent optimizes:

- **Bundle Size** — Tree-shaking, Code Splitting
- **Render Performance** — memo(), useMemo(), useCallback()
- **Image Optimization** — Lazy loading, WebP, Responsive Images
- **CSS Optimization** — Purge unused, CSS-in-JS optimization
- **Type Checking** — TypeScript strict mode

---

## 🔧 Konfiguration

### `frontend_agent_config.yaml`
```yaml
agent:
  name: "Frontend Agent"
  model_primary: "claude-code"
  model_docstring: "ollama:mistral"
  fallback_models:
    - "codex:gpt-5.2-codex"
    - "github-copilot"

frameworks:
  react:
    version: "18+"
    test_framework: jest
    testing_library: "@testing-library/react"
  
task_config:
  max_concurrent: 5
  timeout_minutes: 30
  auto_commit: true
  auto_push: true

quality_gates:
  min_coverage: 80
  require_jsdoc: true
  require_tests: true
  a11y_level: "AA"
  lighthouse_score_min: 80
```

---

## 📈 Metriken

Frontend Agent tracked:

| Metrik | Beschreibung |
|--------|---|
| `components_created` | Neue Components |
| `tests_coverage` | % Code mit Tests |
| `a11y_issues_fixed` | Accessibility Fixes |
| `lighthouse_score` | Performance Score |
| `bundle_size` | KB (sollte sinken) |

Logs → `/home/shares/beermann/logs/frontend_agent.log`

---

**Status:** ✅ Live & Running  
**Letzte Update:** 2026-03-10  
**Nächster Review:** 2026-03-17
