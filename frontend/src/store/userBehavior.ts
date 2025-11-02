/**
 * User Behavior Store - Tracks user feedback and preferences for AI advisor
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface FeedbackEntry {
  itemId: string
  recommendationId: string
  feedbackType: 'helpful' | 'not_helpful' | 'accurate' | 'inaccurate'
  timestamp: string
  actualOutcome?: {
    won: boolean
    finalPrice?: number
    profitable?: boolean
  }
  comment?: string
}

export interface UserPreferences {
  preferredCategories: string[]
  maxBudgetPerItem: number
  riskTolerance: 'low' | 'medium' | 'high'
  autoRefreshRecommendations: boolean
}

export interface BiddingActivity {
  itemId: string
  category: string
  bidAmount: number
  won: boolean
  timestamp: string
}

interface UserBehaviorStore {
  // Feedback history
  feedback: FeedbackEntry[]
  addFeedback: (feedback: Omit<FeedbackEntry, 'timestamp'>) => void
  getFeedbackForItem: (itemId: string) => FeedbackEntry[]
  
  // User preferences
  preferences: UserPreferences
  updatePreferences: (preferences: Partial<UserPreferences>) => void
  
  // Bidding history
  biddingHistory: BiddingActivity[]
  addBiddingActivity: (activity: Omit<BiddingActivity, 'timestamp'>) => void
  getBiddingHistoryForCategory: (category: string) => BiddingActivity[]
  
  // Analytics
  getTotalFeedback: () => {
    helpful: number
    not_helpful: number
    accurate: number
    inaccurate: number
  }
  getCategorySuccessRate: (category: string) => number
  getAverageBidAmount: () => number
  
  // Clear data
  clearFeedback: () => void
  clearBiddingHistory: () => void
  resetAll: () => void
}

const DEFAULT_PREFERENCES: UserPreferences = {
  preferredCategories: [],
  maxBudgetPerItem: 1000,
  riskTolerance: 'medium',
  autoRefreshRecommendations: true
}

export const useUserBehaviorStore = create<UserBehaviorStore>()(
  persist(
    (set, get) => ({
      // Initial state
      feedback: [],
      preferences: DEFAULT_PREFERENCES,
      biddingHistory: [],
      
      // Feedback actions
      addFeedback: (feedbackData) => {
        const newFeedback: FeedbackEntry = {
          ...feedbackData,
          timestamp: new Date().toISOString()
        }
        
        set((state) => ({
          feedback: [...state.feedback, newFeedback]
        }))
      },
      
      getFeedbackForItem: (itemId) => {
        return get().feedback.filter((f) => f.itemId === itemId)
      },
      
      // Preferences actions
      updatePreferences: (updates) => {
        set((state) => ({
          preferences: {
            ...state.preferences,
            ...updates
          }
        }))
      },
      
      // Bidding history actions
      addBiddingActivity: (activityData) => {
        const newActivity: BiddingActivity = {
          ...activityData,
          timestamp: new Date().toISOString()
        }
        
        set((state) => ({
          biddingHistory: [...state.biddingHistory, newActivity]
        }))
      },
      
      getBiddingHistoryForCategory: (category) => {
        return get().biddingHistory.filter((a) => a.category === category)
      },
      
      // Analytics actions
      getTotalFeedback: () => {
        const feedback = get().feedback
        
        return {
          helpful: feedback.filter((f) => f.feedbackType === 'helpful').length,
          not_helpful: feedback.filter((f) => f.feedbackType === 'not_helpful').length,
          accurate: feedback.filter((f) => f.feedbackType === 'accurate').length,
          inaccurate: feedback.filter((f) => f.feedbackType === 'inaccurate').length
        }
      },
      
      getCategorySuccessRate: (category) => {
        const categoryHistory = get().getBiddingHistoryForCategory(category)
        
        if (categoryHistory.length === 0) {
          return 0
        }
        
        const wins = categoryHistory.filter((a) => a.won).length
        return wins / categoryHistory.length
      },
      
      getAverageBidAmount: () => {
        const history = get().biddingHistory
        
        if (history.length === 0) {
          return 0
        }
        
        const total = history.reduce((sum, a) => sum + a.bidAmount, 0)
        return total / history.length
      },
      
      // Clear actions
      clearFeedback: () => {
        set({ feedback: [] })
      },
      
      clearBiddingHistory: () => {
        set({ biddingHistory: [] })
      },
      
      resetAll: () => {
        set({
          feedback: [],
          preferences: DEFAULT_PREFERENCES,
          biddingHistory: []
        })
      }
    }),
    {
      name: 'user-behavior-storage', // Storage key in localStorage
      partialize: (state) => ({
        feedback: state.feedback.slice(-100), // Keep last 100 feedback entries
        preferences: state.preferences,
        biddingHistory: state.biddingHistory.slice(-200) // Keep last 200 bidding activities
      })
    }
  )
)

// Export helper hooks
export const useUserPreferences = () => {
  const preferences = useUserBehaviorStore((state) => state.preferences)
  const updatePreferences = useUserBehaviorStore((state) => state.updatePreferences)
  return { preferences, updatePreferences }
}

export const useFeedback = () => {
  const addFeedback = useUserBehaviorStore((state) => state.addFeedback)
  const getTotalFeedback = useUserBehaviorStore((state) => state.getTotalFeedback)
  return { addFeedback, getTotalFeedback }
}

export const useBiddingHistory = () => {
  const biddingHistory = useUserBehaviorStore((state) => state.biddingHistory)
  const addBiddingActivity = useUserBehaviorStore((state) => state.addBiddingActivity)
  const getCategorySuccessRate = useUserBehaviorStore((state) => state.getCategorySuccessRate)
  const getAverageBidAmount = useUserBehaviorStore((state) => state.getAverageBidAmount)
  
  return {
    biddingHistory,
    addBiddingActivity,
    getCategorySuccessRate,
    getAverageBidAmount
  }
}
