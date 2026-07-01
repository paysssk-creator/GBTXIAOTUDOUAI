# 🥔 GBT小土豆创造助手 - 重新设计方案

## 🎯 设计理念
**极简、聚焦、专业** - 专注于AI代码生成的核心体验

## 📐 新的UI设计

### 1. **主界面重构**
```
┌─────────────────────────────────────────┐
│  🌱 GBT小土豆创造助手                     │
├─────────────────────────────────────────┤
│                                         │
│  💬 我要创建...                          │
│  ┌─────────────────────────────────┐   │
│  │ 做一个LRU缓存类，配单元测试       │   │
│  └─────────────────────────────────┘   │
│                                         │
│  [🧠 理解需求]  [⚡ 开始创造]             │
│                                         │
│  ────────────────────────────────      │
│                                         │
│  📊 创造进度                            │
│  ┌─────────────────────────────────┐   │
│  │ ● 理解需求                          │   │
│ │ ● 生成代码                          │   │
│  │ ● 运行测试                          │   │
│  │ ● 输出结果                          │   │
│  └─────────────────────────────────┘   │
│                                         │
└─────────────────────────────────────────┘
```

### 2. **核心功能聚焦**
- **主要功能**：AI代码生成（唯一核心）
- **辅助功能**：
  - 模型选择（侧边栏）
  - 设置（右上角）
  - 历史记录（侧边栏）

### 3. **视觉设计规范**
- **配色方案**：
  - 主色：绿色 (#4ade80) - 代表生长和创造
  - 背景色：深灰 (#07080c) - 专业感
  - 文字：白色 (#eef1f8) - 可读性

- **字体系统**：
  - 标题：18px, font-weight: 600
  - 正文：14px, font-weight: 400
  - 说明：12px, color: #6b7394

- **间距系统**：
  - 大间距：24px
  - 中间距：16px
  - 小间距：8px

## 🏗️ 架构重构

### 1. **模块化设计**
```
src/
├── core/                 # 核心功能
│   ├── ai/              # AI交互
│   ├── codegen/         # 代码生成
│   ├── testing/         # 测试执行
│   └── sandbox/         # 沙盒环境
├── ui/                  # 用户界面
│   ├── components/     # 可复用组件
│   ├── hooks/          # React Hooks
│   └── styles/         # 样式
├── config/             # 配置
└── utils/              # 工具函数
```

### 2. **状态管理**
使用简单的Context API，避免过度工程化：

```typescript
// 核心状态
interface AppState {
  currentTask: Task | null;
  isProcessing: boolean;
  progress: ProgressStep[];
  settings: AppSettings;
}

// 任务状态
interface Task {
  id: string;
  description: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  result?: TaskResult;
}
```

### 3. **用户体验流程**
```
用户输入 → AI理解 → 代码生成 → 测试验证 → 结果输出
    ↓         ↓         ↓         ↓         ↓
  简单直观  清晰反馈  快速生成  可靠验证  完整输出
```

## 🎨 具体实现

### 1. **主界面组件**
```typescript
// App.tsx
function App() {
  return (
    <div className="app">
      <Header />
      <MainInput />
      <ProgressIndicator />
      <ResultOutput />
    </div>
  );
}
```

### 2. **核心功能组件**
```typescript
// MainInput.tsx
function MainInput() {
  const [input, setInput] = useState('');
  
  return (
    <div className="main-input">
      <textarea
        placeholder="描述你想要创建的程序..."
        value={input}
        onChange={(e) => setInput(e.target.value)}
      />
      <div className="actions">
        <button onClick={handleUnderstand}>🧠 理解需求</button>
        <button onClick={handleCreate} disabled={!input}>
          ⚡ 开始创造
        </button>
      </div>
    </div>
  );
}
```

### 3. **进度指示器**
```typescript
// ProgressIndicator.tsx
function ProgressIndicator() {
  const steps = [
    { id: 'understand', name: '理解需求', status: 'completed' },
    { id: 'generate', name: '生成代码', status: 'current' },
    { id: 'test', name: '运行测试', status: 'pending' },
    { id: 'output', name: '输出结果', status: 'pending' },
  ];
  
  return (
    <div className="progress">
      {steps.map(step => (
        <Step key={step.id} step={step} />
      ))}
    </div>
  );
}
```

## 🚀 实施计划

### 第一阶段：基础重构
1. 创建新的UI组件结构
2. 实现核心输入界面
3. 添加基础的进度显示

### 第二阶段：功能优化
1. 优化AI交互流程
2. 改进代码生成逻辑
3. 增强测试反馈

### 第三阶段：体验提升
1. 添加动画效果
2. 优化响应式设计
3. 完善错误处理

## 📋 设计原则

1. **少即是多**：移除不必要的功能
2. **渐进式披露**：按需显示信息
3. **即时反馈**：每个操作都有明确反馈
4. **容错设计**：允许用户撤销和重试
5. **一致性**：保持界面和交互的一致性

这个重新设计方案将使GBT小土豆创造助手更加专业、易用和聚焦于核心价值。