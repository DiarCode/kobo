import ky from 'ky'
import type { Menu } from '../types/menu.types'

class MenuService {
  private readonly baseUrl = '/api/v1/menu'

  async getMenu(restaurantId: string) {
    return await ky<Menu>(`${this.baseUrl}/${restaurantId}`).json()
  }
}

export const menuService = new MenuService()
