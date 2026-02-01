import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import viteTsconfigPaths from 'vite-tsconfig-paths';
import svgrPlugin from 'vite-plugin-svgr';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react(), viteTsconfigPaths(), svgrPlugin()],
  // 👇 核心修改：请一定要改成这一行，前后都要有斜杠！
  base: '/workouts_page/', 
  build: {
    manifest: true,
    outDir: './dist',
  },
});
