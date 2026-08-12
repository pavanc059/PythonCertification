import type { NewsArticle } from '@/api/market'

/**
 * Pure filter that returns only breaking news articles.
 * Result is a subset of the input where every element has is_breaking === true.
 */
export function filterBreakingNews(articles: NewsArticle[]): NewsArticle[] {
  return articles.filter((a) => a.is_breaking === true)
}
