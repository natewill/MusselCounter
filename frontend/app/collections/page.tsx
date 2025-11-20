'use client';

import { useRef } from 'react';
import Title from '@/components/collections/Title';
import SearchBar from '@/components/collections/SearchBar';

export default function CollectionHistoryPage() {

    return (
        <div className="min-h-screen bg-zinc-50 dark:bg-black p-8">
            <div className="max-w-6xl mx-auto">
                <Title/>
            </div>

            <div className="flex justify-center">
                <SearchBar/>
            </div>

        </div>

    );
}