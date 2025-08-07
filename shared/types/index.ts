/**
 * Shared Types
 * 
 * Common TypeScript interfaces and types used across the FixitAI application.
 */

// User-related types
export interface User {
  id: string;
  username: string;
  email: string;
  avatar?: string;
  skillLevel: 'beginner' | 'intermediate' | 'advanced' | 'expert';
  joinDate: Date;
  repairCount: number;
  followers: number;
  following: number;
  isVerified: boolean;
}

// Repair-related types
export interface Repair {
  id: string;
  userId: string;
  title: string;
  description: string;
  itemType: string;
  damageType: string[];
  difficulty: 'easy' | 'medium' | 'hard' | 'expert';
  status: 'in_progress' | 'completed' | 'abandoned' | 'escalated';
  estimatedTime: string;
  actualTime?: string;
  toolsNeeded: string[];
  instructions: RepairInstruction[];
  beforeImage: string;
  afterImage?: string;
  createdAt: Date;
  updatedAt: Date;
  completedAt?: Date;
}

export interface RepairInstruction {
  step: number;
  title: string;
  description: string;
  image?: string;
  video?: string;
  estimatedTime: string;
  tools: string[];
  warnings?: string[];
  isCompleted?: boolean;
}

// AI and Analysis types
export interface AIAnalysis {
  itemType: string;
  damageType: string[];
  severity: 'minor' | 'moderate' | 'severe';
  confidence: number;
  suggestedTools: string[];
  estimatedDifficulty: string;
  safetyWarnings: string[];
}

// Social types
export interface SocialPost {
  id: string;
  userId: string;
  type: 'repair' | 'tip' | 'question' | 'achievement';
  content: {
    title: string;
    description: string;
    images: string[];
    tags: string[];
  };
  metrics: {
    likes: number;
    comments: number;
    shares: number;
  };
  userInteractions: {
    isLiked: boolean;
    isSaved: boolean;
  };
  timestamp: Date;
}

// API Response types
export interface APIResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
  timestamp: Date;
}

export interface PaginatedResponse<T> {
  data: T[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    totalPages: number;
  };
}

// Error types
export interface AppError {
  code: string;
  message: string;
  details?: any;
  timestamp: Date;
}

// Configuration types
export interface AppConfig {
  environment: 'development' | 'staging' | 'production';
  apiBaseUrl: string;
  imageUploadUrl: string;
  maxImageSize: number;
  supportedImageTypes: string[];
  maxDescriptionLength: number;
}
