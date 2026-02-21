import { useQuery } from '@tanstack/vue-query'
import { computed, unref, type MaybeRef } from 'vue'
import { menuService } from '../services/menu.service'

const MENU_QUERY_KEYS = {
  all: ['menu'] as const,
  byRestaurant: (restaurantId: string) => [...MENU_QUERY_KEYS.all, restaurantId] as const,
} as const

export const useGetMenu = (restaurantId: MaybeRef<string>) => {
  const resolvedRestaurantId = computed<string>(() => {
    return unref(restaurantId)
  })
  return useQuery({
    queryKey: MENU_QUERY_KEYS.byRestaurant(resolvedRestaurantId.value),
    queryFn: () => menuService.getMenu(resolvedRestaurantId.value),
  })
}
