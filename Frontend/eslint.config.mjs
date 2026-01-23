import { dirname } from "path";
import { fileURLToPath } from "url";
import { FlatCompat } from "@eslint/eslintrc";
import js from "@eslint/js";
import globals from "globals";
import tsEslint from "@typescript-eslint/eslint-plugin";
import nextPlugin from "eslint-config-next";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const compat = new FlatCompat({
  baseDirectory: __dirname,
});

export default [
  js.configs.recommended,
  ...compat.config({
    ...nextPlugin,
    // 解决 Next.js 配置与扁平化配置的兼容问题
    settings: {
      next: {
        rootDir: "."
      }
    }
  }),
  {
    files: ["**/*.ts", "**/*.tsx"],
    plugins: {
      "@typescript-eslint": tsEslint
    },
    languageOptions: {
      globals: {
        ...globals.browser,
        ...globals.node
      },
      parser: tsEslint.configs.parser, // 使用插件提供的解析器
      parserOptions: {
        project: "./tsconfig.json",
        tsconfigRootDir: __dirname ,
        
        ecmaFeatures: {
          jsx: true
        },
        ecmaVersion: "latest"
      }
    },
    rules: {
      "@typescript-eslint/no-unused-vars": [
        "warn",
        { 
          argsIgnorePattern: "^_",
          varsIgnorePattern: "^_",
          caughtErrorsIgnorePattern: "^_"
        }
      ]
    }
  }
]