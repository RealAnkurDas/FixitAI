/**
 * Application Constants
 * 
 * Global constants used throughout the FixitAI application.
 */

// API Endpoints
export const API_ENDPOINTS = {
  AUTH: {
    LOGIN: '/auth/login',
    REGISTER: '/auth/register',
    LOGOUT: '/auth/logout',
    REFRESH: '/auth/refresh',
  },
  REPAIRS: {
    CREATE: '/repairs',
    GET_ALL: '/repairs',
    GET_BY_ID: '/repairs/:id',
    UPDATE: '/repairs/:id',
    DELETE: '/repairs/:id',
    ANALYZE: '/repairs/analyze',
  },
  SOCIAL: {
    POSTS: '/social/posts',
    LIKES: '/social/likes',
    COMMENTS: '/social/comments',
    FOLLOWERS: '/social/followers',
  },
  EXPERTS: {
    SEARCH: '/experts/search',
    DETAILS: '/experts/:id',
    BOOK: '/experts/:id/book',
  },
  AI: {
    GEMINI: '/ai/gemini',
    MCP: '/ai/mcp',
    ANALYSIS: '/ai/analysis',
  },
} as const;

// Difficulty Levels
export const DIFFICULTY_LEVELS = {
  EASY: 'easy',
  MEDIUM: 'medium',
  HARD: 'hard',
  EXPERT: 'expert',
} as const;

// Repair Status
export const REPAIR_STATUS = {
  IN_PROGRESS: 'in_progress',
  COMPLETED: 'completed',
  ABANDONED: 'abandoned',
  ESCALATED: 'escalated',
} as const;

// User Skill Levels
export const SKILL_LEVELS = {
  BEGINNER: 'beginner',
  INTERMEDIATE: 'intermediate',
  ADVANCED: 'advanced',
  EXPERT: 'expert',
} as const;

// Image Configuration
export const IMAGE_CONFIG = {
  MAX_SIZE: 10 * 1024 * 1024, // 10MB
  SUPPORTED_TYPES: ['image/jpeg', 'image/png', 'image/webp'],
  MAX_WIDTH: 1920,
  MAX_HEIGHT: 1080,
  QUALITY: 0.8,
} as const;

// Text Limits
export const TEXT_LIMITS = {
  DESCRIPTION_MAX: 500,
  TITLE_MAX: 100,
  COMMENT_MAX: 1000,
  TAG_MAX: 10,
} as const;

// Pagination
export const PAGINATION = {
  DEFAULT_PAGE: 1,
  DEFAULT_LIMIT: 20,
  MAX_LIMIT: 100,
} as const;

// Time Formats
export const TIME_FORMATS = {
  DISPLAY: 'MMM dd, yyyy',
  TIMESTAMP: 'yyyy-MM-dd HH:mm:ss',
  RELATIVE: 'relative',
} as const;

// Error Codes
export const ERROR_CODES = {
  NETWORK_ERROR: 'NETWORK_ERROR',
  AUTH_ERROR: 'AUTH_ERROR',
  VALIDATION_ERROR: 'VALIDATION_ERROR',
  PERMISSION_ERROR: 'PERMISSION_ERROR',
  NOT_FOUND: 'NOT_FOUND',
  SERVER_ERROR: 'SERVER_ERROR',
} as const;

// Feature Flags
export const FEATURE_FLAGS = {
  VOICE_INPUT: true,
  SOCIAL_FEED: true,
  EXPERT_FINDER: true,
  AI_ANALYSIS: true,
  OFFLINE_MODE: false,
} as const;

// Animation Durations
export const ANIMATION_DURATIONS = {
  FAST: 200,
  NORMAL: 300,
  SLOW: 500,
} as const;

// Storage Keys
export const STORAGE_KEYS = {
  USER_TOKEN: 'user_token',
  USER_PROFILE: 'user_profile',
  APP_SETTINGS: 'app_settings',
  OFFLINE_DATA: 'offline_data',
} as const;
