'use client';

import dynamic from 'next/dynamic';

// 动态导入预分诊页面组件，并禁用SSR以避免客户端API在服务端执行出错
const TriagePage = dynamic(() => import('@/app/components/pre-diagnosis-page'), {
  loading: () => <p>正在加载预分诊系统...</p>, // 添加加载状态
  ssr: false, // 禁用服务器端渲染
});

export default function Home() {
  return (
    <main className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4"> MedSynthAi</h1>
      <TriagePage />
    </main>
  );
}