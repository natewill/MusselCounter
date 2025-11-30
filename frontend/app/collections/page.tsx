'use client';

import { useRef } from 'react';
import { useState, useEffect } from 'react';
import Title from '@/components/collections/Title';
import SearchBar from '@/components/collections/SearchBar';
import CollectionList from '@/components/collections/CollectionList';
import { getImageDetails } from '@/lib/api';
import { useParams, useSearchParams, useRouter } from 'next/navigation';

const getFilteredCollections = (runId, imageId) => {
    if (!runId){
        return imageId
    }
    return imageId.filter()
}
export default function CollectionHistoryPage() {

    const params = useParams();
    const searchParams = useSearchParams();
    const router = useRouter();
    const imageId = parseInt(Array.isArray(params.imageId) ? params.imageId[0] : params.imageId || '0', 10);
    const runId = parseInt(searchParams.get('runId') || '0', 10);

    const filteredCollections = getFilteredCollections(runId, imageId)
    return (
        <div className="min-h-screen bg-zinc-50 dark:bg-black p-8">
            
            <Title/>
            
            <SearchBar/>
            <ul>
                
            </ul>
            
            <CollectionList/>

        </div>

    );
}