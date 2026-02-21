<script setup lang="ts">
import { useGetMenu } from '../composables/menu.composable'
import { Button } from '@/core/components/ui/button'
const menu = useGetMenu('1')
</script>

<template>
  <div>Menu {{ menu }}</div>
  <Button>Order</Button>
</template>

<style scoped></style>
