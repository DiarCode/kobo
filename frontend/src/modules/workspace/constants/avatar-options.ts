import avatar1 from '@/core/assets/charachters/1_female.png'
import avatar2 from '@/core/assets/charachters/2_male.png'
import avatar3 from '@/core/assets/charachters/3_male.png'
import avatar4 from '@/core/assets/charachters/4_male.png'
import avatar5 from '@/core/assets/charachters/5_female.png'
import avatar6 from '@/core/assets/charachters/6_female.png'
import avatar7 from '@/core/assets/charachters/7_male.png'
import avatar8 from '@/core/assets/charachters/8_male.png'
import avatar9 from '@/core/assets/charachters/9_male.png'

export interface AvatarOption {
  key: string
  src: string
}

export const AVATAR_OPTIONS: AvatarOption[] = [
  { key: 'char1', src: avatar1 },
  { key: 'char2', src: avatar2 },
  { key: 'char3', src: avatar3 },
  { key: 'char4', src: avatar4 },
  { key: 'char5', src: avatar5 },
  { key: 'char6', src: avatar6 },
  { key: 'char7', src: avatar7 },
  { key: 'char8', src: avatar8 },
  { key: 'char9', src: avatar9 },
]
