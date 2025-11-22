'use client';

import { useRef } from 'react';
import Title from '@/components/collections/Title';
import SearchBar from '@/components/collections/SearchBar';
import CollectionList from '@/components/collections/CollectionList';

export default function CollectionHistoryPage() {

    return (
        <div className="min-h-screen bg-zinc-50 dark:bg-black p-8">
            
            <Title/>
            
            <SearchBar/>
            
            <CollectionList/>

        </div>

    );
}